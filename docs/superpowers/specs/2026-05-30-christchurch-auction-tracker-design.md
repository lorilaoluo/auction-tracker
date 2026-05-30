# Christchurch Auction Results Tracker — Design Spec

**Date:** 2026-05-30
**Status:** Draft

## Purpose

A manually-triggered Python CLI tool that scrapes auction/sold results from Christchurch real estate agency websites, stores them locally, and provides a Streamlit dashboard to view price trends. The goal is to inform the user's house-buying decisions with real sold-price data.

## Architecture

```
auction-tracker/
  auction_tracker/
    __init__.py
    cli.py              # CLI entry point (scrape, view, stats)
    database.py         # SQLite connection, schema, insert/query
    scraper/
      __init__.py
      base.py           # BaseScraper class with shared logic
      holmwood.py       # Holmwood scraper
      grenadier.py      # Grenadier scraper
      bayleys.py        # (future)
      harcourts.py      # (future)
      raywhite.py       # (future)
    dashboard.py        # Streamlit app (overview, trends, explore)
    models.py           # Pydantic models for validation
  tests/
    fixtures/
      holmwood_sample.html
      grenadier_sample.html
    test_parsing.py
    test_database.py
    test_deduplication.py
  docs/superpowers/specs/
    2026-05-30-christchurch-auction-tracker-design.md
```

## Components

### 1. Scrapers (one per agency)

Each scraper extends `BaseScraper` and implements `scrape() -> list[dict]`. Returns a list of standardized dictionaries:

```python
{
    "address": str,
    "suburb": str,
    "sale_price": float | None,   # None if price undisclosed
    "sale_date": date,
    "agency": str,
    "bedrooms": int | None,
    "bathrooms": int | None,
    "property_type": str | None,
    "source_url": str,
}
```

- **Initial agencies:** Holmwood (holmwood.co.nz), Grenadier (grenadier.co.nz)
- **Future agencies:** Bayleys, Harcourts, Ray White
- **Scraping approach:** requests + BeautifulSoup first; Playwright fallback if JS-rendering needed
- **Politeness:** 2-5 second random delay between requests
- **Deduplication:** Check address + sale_date + sale_price before insert; skip duplicates
- **Resilience:** One scraper failing does not stop others. Report partial results.

### 2. SQLite Database

Single file `auction_results.db` in the project root.

**Schema:**
```sql
CREATE TABLE auction_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    address TEXT NOT NULL,
    suburb TEXT NOT NULL,
    sale_price REAL,
    sale_date DATE NOT NULL,
    agency TEXT NOT NULL,
    bedrooms INTEGER,
    bathrooms INTEGER,
    property_type TEXT,
    source_url TEXT,
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(address, sale_date, sale_price)
);
```

### 3. CLI

Three commands via `click` or `argparse`:

- `auction-tracker scrape` — Run all scrapers, print summary ("Holmwood: 12 new. Grenadier: 5 new. 2 failed: Ray White (timeout)"). Exit code 0 if any scraper succeeded; exit code 1 only if ALL scrapers failed.
- `auction-tracker view` — Launch Streamlit dashboard on localhost:8501
- `auction-tracker stats` — Print quick text summary: total records, median price, most recent scrape date per agency

### 4. Streamlit Dashboard

Three tabs:

**Overview tab:**
- Total sales tracked, median sale price, average sale price, highest/lowest sale
- "Last scraped" timestamp per agency

**Trends tab:**
- Median sale price over time (line chart, monthly/weekly toggle)
- Number of sales over time (line chart)
- Suburb filter dropdown

**Explore tab:**
- Filterable data table (suburb, price range, bedrooms, agency, date)
- Median price by suburb bar chart (top 15 suburbs)
- Click a row for full property details

## Error Handling

- **Partial scraper failures:** If some scrapers fail, CLI prints a summary noting which succeeded and which failed. Exit code 0 as long as at least one scraper produced results. Exit code 1 only if ALL scrapers fail.
- **Zero new results:** Print "0 new results" so the user can investigate if expected data is missing.
- **Invalid/missing prices:** Store as NULL. Dashboard shows "Price not disclosed." These rows are excluded from price statistics but counted in volume stats.
- **Duplicate detection:** UNIQUE constraint on (address, sale_date, sale_price). Safe to run scrape repeatedly.
- **Validation before insert:** Required fields: address, sale_date, agency. Bad rows logged and skipped.

### Growth Scenario: 4+ Years of Data

When the dataset grows large (e.g., thousands of rows across several years of weekly scrapes), the dashboard should stay responsive. Mitigations:
- **SQLite handles this well up to hundreds of thousands of rows** with proper indexing
- Add indexes on `sale_date` and `suburb` for filtered queries
- Streamlit caches query results per session, so repeated chart renders don't re-hit the DB
- For the Trends tab, pre-aggregating monthly medians in a materialized view or summary table can speed up the line charts. This is a future optimization — start simple, add only if needed.

## Testing

- **Parsing tests:** Unit tests run scraping logic against saved HTML snapshots from real agency pages. Verifies address/price/date extraction is correct.
- **Data validation tests:** Test deduplication, price normalization, edge cases (missing fields, unusual formats).
- **No integration tests against live sites.**
- Run with `pytest`.

### Test Enforcement

All tests must pass before merging any changes. The user may manually run tests at any point using `pytest`.

## Technical Decisions

- **Python 3.12+**
- **Dependencies:** beautifulsoup4, requests, playwright (optional fallback), streamlit, pandas, pydantic, pytest, click
- **No hosting:** Everything runs locally
- **No scheduling:** Manually triggered via CLI
- **No authentication needed**
