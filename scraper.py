"""Group 7 Steam Top Sellers scraper.

Collects public listing data from Steam's Top Sellers search results.
Respect the course assignment's request delay and Steam's current robots.txt.
This code preserves missing values rather than inventing them.
"""
from __future__ import annotations

import argparse
import logging
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import pandas as pd
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://store.steampowered.com/search/"
OUT_DIR = Path("raw_data")
LOG_DIR = Path("logs")
USER_AGENT = "DSC2107-Group7-Course-Project (contact: julipeace@gmail.com)"
CURRENCY_COUNTRY = "us"   # USD; keep fixed for all seven days
LANGUAGE = "english"

logging.basicConfig(
    filename=LOG_DIR / "scraper.log" if LOG_DIR.exists() else "scraper.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
console = logging.StreamHandler()
console.setLevel(logging.INFO)
logging.getLogger().addHandler(console)


def parse_money(text: Optional[str]) -> Optional[float]:
    """Convert visible price text such as '$19.99' to 19.99; Free becomes 0.0."""
    if not text:
        return None
    clean = text.strip().replace(",", "")
    if re.search(r"\bfree\b", clean, flags=re.I):
        return 0.0
    match = re.search(r"(\d+(?:\.\d{1,2})?)", clean)
    return float(match.group(1)) if match else None


def parse_discount(text: Optional[str]) -> Optional[float]:
    if not text:
        return None
    match = re.search(r"(\d+)\s*%", text)
    return float(match.group(1)) if match else 0.0


def get_text(node) -> Optional[str]:
    if node is None:
        return None
    value = node.get_text(" ", strip=True)
    return value or None


def parse_listing(row, rank: int, scraped_at: str) -> dict:
    app_id = row.get("data-ds-appid", "").split(",")[0].strip()
    title = get_text(row.select_one(".title"))
    release_date = get_text(row.select_one(".search_released"))
    discount_node = row.select_one(".discount_pct")
    original_node = row.select_one(".discount_original_price")
    final_node = row.select_one(".discount_final_price")
    price_node = row.select_one(".search_price")

    discount_text = get_text(discount_node)
    original_text = get_text(original_node)
    final_text = get_text(final_node)

    # On non-discounted listings, .search_price commonly contains the visible price.
    if final_text:
        current_price = parse_money(final_text)
        original_price = parse_money(original_text)
    else:
        price_text = get_text(price_node)
        current_price = parse_money(price_text)
        original_price = current_price

    # Preserve free-to-play price as 0, while absent/unknown price remains null.
    if original_price is None and current_price is not None and current_price == 0:
        original_price = 0.0

    review_node = row.select_one(".search_reviewscore")
    review_summary = None
    if review_node:
        review_summary = (
            review_node.get("data-tooltip-html")
            or review_node.get("data-tooltip-text")
            or get_text(review_node)
        )
        review_summary = BeautifulSoup(str(review_summary), "html.parser").get_text(" ", strip=True)
        review_summary = re.sub(r"\s+", " ", review_summary).strip() or None

    platform_names = []
    for icon in row.select(".search_name .platform_img, .search_name .win, .search_name .mac, .search_name .linux"):
        label = icon.get("aria-label") or icon.get("title")
        if label:
            platform_names.append(label.strip())
        elif "win" in (icon.get("class") or []):
            platform_names.append("Windows")
        elif "mac" in (icon.get("class") or []):
            platform_names.append("macOS")
        elif "linux" in (icon.get("class") or []):
            platform_names.append("Linux")
    # Steam icon class names can change. If no labels were found, keep a missing value.
    platforms = "; ".join(dict.fromkeys(platform_names)) if platform_names else None

    link = row.get("href")
    if not link:
        a = row.select_one("a.search_result_row")
        link = a.get("href") if a else None

    discount = parse_discount(discount_text)
    if discount is None and current_price is not None and original_price is not None:
        if original_price > 0:
            discount = round((original_price - current_price) / original_price * 100, 2)
        elif original_price == 0 and current_price == 0:
            discount = 0.0

    return {
        "game_id": app_id or None,
        "rank": rank,
        "title": title,
        "price": current_price,
        "original_price": original_price,
        "discount_percent": discount,
        "release_date": release_date,
        "review_summary": review_summary,
        "platforms": platforms,
        "currency": "USD",
        "scraped_at": scraped_at,
        "source_url": link,
    }


def fetch_page(session: requests.Session, start: int, timeout: int = 25):
    params = {
        "filter": "topsellers",
        "start": start,
        "count": 50,
        "cc": CURRENCY_COUNTRY,
        "l": LANGUAGE,
    }
    response = session.get(BASE_URL, params=params, timeout=timeout)
    if response.status_code in (403, 429):
        raise RuntimeError(
            f"Steam returned HTTP {response.status_code}. Stop collection, document the block, "
            "and do not attempt to bypass it."
        )
    response.raise_for_status()
    return response.text, response.url


def scrape(limit: int = 500, pages: int = 10, delay: float = 2.5) -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    # Reconfigure file logging once folders exist.
    logging.info("Starting scrape: limit=%s pages=%s delay=%s", limit, pages, delay)
    scraped_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    session = requests.Session()
    session.headers.update({
        "User-Agent": USER_AGENT,
        "Accept-Language": "en-US,en;q=0.9",
    })

    records = []
    seen_ids = set()
    requested_pages = min(pages, (limit + 49) // 50)
    for page_number in range(requested_pages):
        start = page_number * 50
        try:
            html, page_url = fetch_page(session, start)
        except Exception as exc:
            logging.exception("Failed to fetch page start=%s: %s", start, exc)
            break

        soup = BeautifulSoup(html, "html.parser")
        rows = soup.select("a.search_result_row")
        if not rows:
            logging.warning(
                "No result rows found at start=%s. The page structure may have changed; "
                "inspect the HTML and update selectors rather than guessing.", start
            )
            break

        for row in rows:
            app_id = row.get("data-ds-appid", "").split(",")[0].strip()
            if app_id and app_id in seen_ids:
                continue
            if app_id:
                seen_ids.add(app_id)
            record = parse_listing(row, len(records) + 1, scraped_at)
            record["source_url"] = row.get("href") or page_url
            records.append(record)
            if len(records) >= limit:
                break

        logging.info("Fetched start=%s; records collected=%s", start, len(records))
        if len(records) >= limit:
            break
        if page_number < requested_pages - 1:
            time.sleep(max(2.0, delay))

    df = pd.DataFrame(records, columns=[
        "game_id", "rank", "title", "price", "original_price", "discount_percent",
        "release_date", "review_summary", "platforms", "currency", "scraped_at", "source_url"
    ])
    date_stamp = datetime.now().strftime("%Y%m%d")
    output = OUT_DIR / f"steam_top_sellers_{date_stamp}_{datetime.now().strftime('%H%M%S')}.csv"
    df.to_csv(output, index=False)
    logging.info("Saved %s records to %s", len(df), output)
    if len(df) < limit:
        logging.warning("Only %s of requested %s records were collected.", len(df), limit)
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape Steam Top Sellers public listings.")
    parser.add_argument("--limit", type=int, default=500, help="Maximum listings to collect.")
    parser.add_argument("--pages", type=int, default=10, help="Maximum 50-result pages.")
    parser.add_argument("--delay", type=float, default=2.5, help="Seconds between requests (minimum 2).")
    args = parser.parse_args()

    if "REPLACE_WITH_GROUP_CONTACT_EMAIL" in USER_AGENT:
        logging.warning("julipeace@gmail.com")
    scrape(limit=max(1, args.limit), pages=max(1, args.pages), delay=max(2.0, args.delay))
