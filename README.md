# Group 7 — Steam Top Sellers Data Mining & Wrangling Project

**Course:** DSC2107 Data Mining and Wrangling, Year 2  
**Source:** https://store.steampowered.com/search/?filter=topsellers  
**Store region/currency:** US / USD (`cc=us`, `l=english`) — keep this consistent across all runs. Change only if your group agrees and documents it.

## Important honesty note
This folder contains the project code and report/notebook templates. It does **not** contain fabricated Steam observations or pretend that seven daily runs have already happened. Run the scraper daily for seven consecutive days and use the actual output to complete the findings sections.

## Project pipeline
1. Inspect the page and `robots.txt`; document the HTML/network observations in `reports/reconnaissance_note.md`.
2. Run a small test, inspect the CSV and logs.
3. Run the scraper once per day for seven days. Each run requests at most 10 pages of 50 results (up to 500 listings) with a delay between requests.
4. Clean and load the daily raw files into SQLite.
5. Run the notebook to generate six or more charts and analysis tables.
6. Write evidence-based findings in the final report and presentation.

## Setup (Windows)
1. Install Python 3.10+.
2. Extract this ZIP to a folder.
3. Open Command Prompt or terminal in that folder.
4. Create a virtual environment (optional but recommended):
   `python -m venv .venv`
   Windows: `.venv\\Scripts\\activate`
   macOS/Linux: `source .venv/bin/activate`
5. Install dependencies:
   `python -m pip install -r requirements.txt`

## Run a sample collection
The assignment says at least 100 products for the first sample run. For a low-impact test, use:
`python scraper.py --limit 100 --pages 2`

Then check `raw_data/` for a dated CSV and `logs/scraper.log`.

## Run the daily collection
`python scraper.py --limit 500 --pages 10`

Run this command once a day for seven consecutive days. The script has a default 2.5-second delay between page requests and stops on access-denied / rate-limit responses rather than trying to bypass protections. Do not run repeatedly just to force a result.

**Do not claim 500 records if fewer than 500 were actually returned.** Document the real count and any limitations.

## Clean and load
`python clean_and_load.py`

This reads all `raw_data/steam_top_sellers_*.csv` files, writes a cleaned combined CSV to `cleaned_data/steam_observations_cleaned.csv`, and creates/updates `steam_games.db`.

## Analysis notebook
Start Jupyter:
`jupyter notebook`
Open `notebooks/Group7_Analysis.ipynb`, then run all cells. If the notebook says there is no database or no observations, collect data first.

## Scheduling
Use Windows Task Scheduler, cron, or run the command manually each day. If using a scheduler, verify that it creates a file and logs a successful run. The assignment's seven-day collection cannot be recreated honestly by running seven times on the same day.

## Required fields
`game_id`, `rank`, `title`, `price`, `original_price`, `discount_percent`, `release_date`, `review_summary`, `platforms`, `currency`, `scraped_at`, `source_url`.

The Steam search listing may not expose every field for every product. Missing values are retained as missing and should be discussed in the report; the script does not invent values. A stable Steam app ID is used when available.

## Database design
- `products`: one record per unique Steam app ID, title, release date, platforms, source URL.
- `observations`: one record per app per scrape timestamp, including rank, price, original price, discount, review summary, currency.

## Ethics and limitations
- `robots.txt` was checked during project preparation. It disallows certain paths, including `/share/`, `/news/externalpost/`, and some account/email paths. This scraper targets the public search page, not those disallowed paths. Re-check the current rules before running.
- The assignment requires a delay of 2–5 seconds between requests and roughly 1,000 requests or fewer per daily run.
- Use public, logged-out pages only. Do not collect personal data, bypass CAPTCHAs, rotate proxies to evade blocks, or spoof identity.
- Steam rankings are revenue-related rankings and can include DLC/hardware as well as games; do not describe them as pure unit sales or game-only rankings without filtering and explaining your decision.
- Prices and rankings are regional and time-sensitive. This project pins the store to the US region/currency for consistency; document this choice.
- The site may change its HTML. Validate selectors and inspect logs if fields are missing.

## Suggested report structure (5–8 pages)
1. Title page
2. Introduction and objectives
3. Data source, reconnaissance and ethics
4. Methodology (scraping, cleaning, database)
5. Results and six charts (insert real results)
6. Answers to core questions + one original question
7. Limitations and conclusion
8. References

