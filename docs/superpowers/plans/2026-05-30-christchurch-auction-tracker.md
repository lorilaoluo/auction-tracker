# Christchurch Auction Tracker — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python CLI tool that scrapes Christchurch real estate auction/sold results, stores them in SQLite, and provides a Streamlit dashboard for price trend analysis.

**Architecture:** A single Python package with three layers — Playwright-based scrapers (one per agency), a SQLite database layer with Pydantic models, and a Streamlit dashboard with three tabs (Overview, Trends, Explore). CLI wires them together with `scrape`, `view`, and `stats` commands.

**Tech Stack:** Python 3.12+, Playwright, BeautifulSoup4, Streamlit, Pandas, Pydantic, pytest, Click

**Spec:** `docs/superpowers/specs/2026-05-30-christchurch-auction-tracker-design.md`

---

### Task 1: Project Scaffolding

**Files:**
- Create: `auction-tracker/pyproject.toml`
- Create: `auction-tracker/auction_tracker/__init__.py`
- Create: `auction-tracker/tests/__init__.py`
- Create: `auction-tracker/tests/fixtures/.gitkeep`

- [ ] **Step 1: Create pyproject.toml**

```toml
[build-system]
requires = ["setuptools>=68.0"]
build-backend = "setuptools.backends._legacy:_Backend"

[project]
name = "auction-tracker"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "beautifulsoup4>=4.12",
    "click>=8.1",
    "pandas>=2.2",
    "playwright>=1.40",
    "pydantic>=2.5",
    "streamlit>=1.29",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
]

[project.scripts]
auction-tracker = "auction_tracker.cli:main"
```

- [ ] **Step 2: Create `auction_tracker/__init__.py`**

```python
"""Christchurch Auction Results Tracker."""
```

- [ ] **Step 3: Create `tests/__init__.py`** (empty file)

- [ ] **Step 4: Create fixtures directory**

Run: `mkdir -p auction-tracker/tests/fixtures && touch auction-tracker/tests/fixtures/.gitkeep`

- [ ] **Step 5: Install the project in development mode**

Run: `cd auction-tracker && pip install -e ".[dev]" && playwright install chromium`
Expected: Dependencies install successfully, Playwright downloads Chromium

- [ ] **Step 6: Commit**

```bash
cd auction-tracker && git init && git add -A && git commit -m "feat: scaffold project with pyproject.toml and dependencies"
```

---

### Task 2: Pydantic Models

**Files:**
- Create: `auction-tracker/auction_tracker/models.py`
- Create: `auction-tracker/tests/test_models.py`

- [ ] **Step 1: Write the failing test**

```python
"""Tests for data models."""
import pytest
from datetime import date
from auction_tracker.models import AuctionResult, ScrapeReport


class TestAuctionResult:
    def test_valid_result(self):
        r = AuctionResult(
            address="12 Example St",
            suburb="Riccarton",
            sale_price=850_000,
            sale_date=date(2026, 5, 15),
            agency="Holmwood",
            source_url="https://holmwood.co.nz/listing/123",
        )
        assert r.address == "12 Example St"
        assert r.sale_price == 850_000

    def test_price_can_be_none(self):
        r = AuctionResult(
            address="12 Example St",
            suburb="Riccarton",
            sale_price=None,
            sale_date=date(2026, 5, 15),
            agency="Holmwood",
            source_url="https://holmwood.co.nz/listing/123",
        )
        assert r.sale_price is None

    def test_optional_fields_default_to_none(self):
        r = AuctionResult(
            address="12 Example St",
            suburb="Riccarton",
            sale_price=500_000,
            sale_date=date(2026, 5, 15),
            agency="Holmwood",
            source_url="https://holmwood.co.nz/listing/123",
        )
        assert r.bedrooms is None
        assert r.bathrooms is None
        assert r.property_type is None

    def test_address_is_required(self):
        with pytest.raises(ValueError):
            AuctionResult(
                suburb="Riccarton",
                sale_price=500_000,
                sale_date=date(2026, 5, 15),
                agency="Holmwood",
                source_url="https://holmwood.co.nz/listing/123",
            )

    def test_agency_is_required(self):
        with pytest.raises(ValueError):
            AuctionResult(
                address="12 Example St",
                suburb="Riccarton",
                sale_price=500_000,
                sale_date=date(2026, 5, 15),
                source_url="https://holmwood.co.nz/listing/123",
            )


class TestScrapeReport:
    def test_all_success(self):
        report = ScrapeReport(
            agency_results={"Holmwood": 12, "Grenadier": 5},
            errors={},
        )
        assert report.all_failed is False
        assert report.total_new == 17

    def test_partial_failure(self):
        report = ScrapeReport(
            agency_results={"Holmwood": 12},
            errors={"Grenadier": "HTTP 403"},
        )
        assert report.all_failed is False
        assert report.total_new == 12

    def test_all_failed(self):
        report = ScrapeReport(
            agency_results={},
            errors={"Holmwood": "Timeout", "Grenadier": "HTTP 403"},
        )
        assert report.all_failed is True
        assert report.total_new == 0

    def test_empty_run(self):
        report = ScrapeReport(
            agency_results={"Holmwood": 0, "Grenadier": 0},
            errors={},
        )
        assert report.all_failed is False
        assert report.total_new == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd auction-tracker && python -m pytest tests/test_models.py -v`
Expected: All tests FAIL — module not found

- [ ] **Step 3: Implement models.py**

```python
"""Data models for auction results."""
from datetime import date
from typing import Optional
from pydantic import BaseModel


class AuctionResult(BaseModel):
    """A single auction/sold result from an agency."""
    address: str
    suburb: str
    sale_price: Optional[float] = None
    sale_date: date
    agency: str
    bedrooms: Optional[int] = None
    bathrooms: Optional[int] = None
    property_type: Optional[str] = None
    source_url: str


class ScrapeReport:
    """Summary of a scrape run across all agencies."""

    def __init__(self, agency_results: dict[str, int], errors: dict[str, str]):
        self.agency_results = agency_results
        self.errors = errors

    @property
    def all_failed(self) -> bool:
        return len(self.agency_results) == 0 and len(self.errors) > 0

    @property
    def total_new(self) -> int:
        return sum(self.agency_results.values())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd auction-tracker && python -m pytest tests/test_models.py -v`
Expected: All 7 tests PASS

- [ ] **Step 5: Commit**

```bash
cd auction-tracker && git add auction_tracker/models.py tests/test_models.py && git commit -m "feat: add Pydantic models for AuctionResult and ScrapeReport"
```

---

### Task 3: Database Layer

**Files:**
- Create: `auction-tracker/auction_tracker/database.py`
- Create: `auction-tracker/tests/test_database.py`

- [ ] **Step 1: Write database tests**

```python
"""Tests for database layer."""
import pytest
from datetime import date
from auction_tracker.database import Database
from auction_tracker.models import AuctionResult


@pytest.fixture
def db():
    database = Database(":memory:")
    yield database
    database.close()


class TestDatabase:
    def test_insert_and_query(self, db):
        result = AuctionResult(
            address="12 Example St",
            suburb="Riccarton",
            sale_price=850_000,
            sale_date=date(2026, 5, 15),
            agency="Holmwood",
            source_url="https://holmwood.co.nz/listing/123",
        )
        inserted = db.insert(result)
        assert inserted == 1

        rows = db.get_all()
        assert len(rows) == 1
        assert rows[0]["address"] == "12 Example St"
        assert rows[0]["sale_price"] == 850_000

    def test_insert_duplicate_is_skipped(self, db):
        result = AuctionResult(
            address="12 Example St",
            suburb="Riccarton",
            sale_price=850_000,
            sale_date=date(2026, 5, 15),
            agency="Holmwood",
            source_url="https://holmwood.co.nz/listing/123",
        )
        assert db.insert(result) == 1
        assert db.insert(result) == 0  # duplicate, skipped
        assert len(db.get_all()) == 1

    def test_insert_different_price_not_duplicate(self, db):
        r1 = AuctionResult(
            address="12 Example St", suburb="Riccarton",
            sale_price=850_000, sale_date=date(2026, 5, 15),
            agency="Holmwood", source_url="https://example.com/1",
        )
        r2 = AuctionResult(
            address="12 Example St", suburb="Riccarton",
            sale_price=860_000, sale_date=date(2026, 5, 15),
            agency="Holmwood", source_url="https://example.com/2",
        )
        assert db.insert(r1) == 1
        assert db.insert(r2) == 1
        assert len(db.get_all()) == 2

    def test_price_null_duplicate_detection(self, db):
        """Two rows with same address+date+both NULL price should be duplicates."""
        r1 = AuctionResult(
            address="12 Example St", suburb="Riccarton",
            sale_price=None, sale_date=date(2026, 5, 15),
            agency="Holmwood", source_url="https://example.com/1",
        )
        r2 = AuctionResult(
            address="12 Example St", suburb="Riccarton",
            sale_price=None, sale_date=date(2026, 5, 15),
            agency="Holmwood", source_url="https://example.com/2",
        )
        assert db.insert(r1) == 1
        assert db.insert(r2) == 0

    def test_get_stats(self, db):
        results = [
            AuctionResult(address="A", suburb="Riccarton", sale_price=800_000,
                          sale_date=date(2026, 5, 15), agency="Holmwood", source_url="x"),
            AuctionResult(address="B", suburb="Riccarton", sale_price=900_000,
                          sale_date=date(2026, 5, 20), agency="Holmwood", source_url="x"),
            AuctionResult(address="C", suburb="Ilam", sale_price=None,
                          sale_date=date(2026, 5, 22), agency="Grenadier", source_url="x"),
        ]
        for r in results:
            db.insert(r)

        stats = db.get_stats()
        assert stats["total"] == 3
        assert stats["median_price"] == 850_000  # median of 800k and 900k (NULL excluded)
        assert stats["avg_price"] == 850_000
        assert stats["min_price"] == 800_000
        assert stats["max_price"] == 900_000

    def test_get_by_suburb(self, db):
        db.insert(AuctionResult(address="A", suburb="Riccarton", sale_price=800_000,
                  sale_date=date(2026, 5, 15), agency="H", source_url="x"))
        db.insert(AuctionResult(address="B", suburb="Ilam", sale_price=900_000,
                  sale_date=date(2026, 5, 20), agency="H", source_url="x"))
        db.insert(AuctionResult(address="C", suburb="Riccarton", sale_price=700_000,
                  sale_date=date(2026, 5, 22), agency="G", source_url="x"))

        riccarton = db.get_by_suburb("Riccarton")
        assert len(riccarton) == 2

    def test_get_last_scrape_per_agency(self, db):
        db.insert(AuctionResult(address="A", suburb="X", sale_price=1,
                  sale_date=date(2026, 5, 15), agency="Holmwood", source_url="x"))
        db.insert(AuctionResult(address="B", suburb="X", sale_price=1,
                  sale_date=date(2026, 5, 20), agency="Grenadier", source_url="x"))

        last = db.get_last_scrape_per_agency()
        assert last["Holmwood"] is not None
        assert last["Grenadier"] is not None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd auction-tracker && python -m pytest tests/test_database.py -v`
Expected: All tests FAIL — module not found

- [ ] **Step 3: Implement database.py**

```python
"""SQLite database layer for auction results."""
import sqlite3
from datetime import date, datetime
from typing import Optional
from auction_tracker.models import AuctionResult


class Database:
    def __init__(self, path: str = "auction_results.db"):
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self._create_schema()

    def _create_schema(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS auction_results (
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
            )
        """)
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_sale_date ON auction_results(sale_date)
        """)
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_suburb ON auction_results(suburb)
        """)
        self.conn.commit()

    def insert(self, result: AuctionResult) -> int:
        """Insert a result. Returns 1 if inserted, 0 if duplicate."""
        try:
            self.conn.execute("""
                INSERT OR IGNORE INTO auction_results
                    (address, suburb, sale_price, sale_date, agency,
                     bedrooms, bathrooms, property_type, source_url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                result.address,
                result.suburb,
                result.sale_price,
                result.sale_date.isoformat(),
                result.agency,
                result.bedrooms,
                result.bathrooms,
                result.property_type,
                result.source_url,
            ))
            self.conn.commit()
            return self.conn.total_changes
        except sqlite3.Error:
            return 0

    def get_all(self, limit: int = 1000) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM auction_results ORDER BY sale_date DESC LIMIT ?",
            (limit,)
        ).fetchall()
        return [dict(r) for r in rows]

    def get_stats(self) -> dict:
        """Return aggregate stats excluding NULL prices."""
        row = self.conn.execute("""
            SELECT
                COUNT(*) as total,
                COUNT(sale_price) as with_price,
                AVG(sale_price) as avg_price,
                MIN(sale_price) as min_price,
                MAX(sale_price) as max_price
            FROM auction_results
        """).fetchone()
        median_row = self.conn.execute("""
            SELECT sale_price FROM auction_results
            WHERE sale_price IS NOT NULL
            ORDER BY sale_price
        """).fetchall()
        median = None
        if median_row:
            prices = [r["sale_price"] for r in median_row]
            n = len(prices)
            if n % 2 == 0:
                median = (prices[n // 2 - 1] + prices[n // 2]) / 2
            else:
                median = prices[n // 2]
        return {
            "total": row["total"],
            "with_price": row["with_price"],
            "avg_price": row["avg_price"],
            "median_price": median,
            "min_price": row["min_price"],
            "max_price": row["max_price"],
        }

    def get_by_suburb(self, suburb: str) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM auction_results WHERE suburb = ? ORDER BY sale_date DESC",
            (suburb,)
        ).fetchall()
        return [dict(r) for r in rows]

    def get_last_scrape_per_agency(self) -> dict[str, Optional[datetime]]:
        rows = self.conn.execute("""
            SELECT agency, MAX(scraped_at) as last_scrape
            FROM auction_results
            GROUP BY agency
        """).fetchall()
        return {r["agency"]: r["last_scrape"] for r in rows}

    def get_all_suburbs(self) -> list[str]:
        rows = self.conn.execute(
            "SELECT DISTINCT suburb FROM auction_results ORDER BY suburb"
        ).fetchall()
        return [r["suburb"] for r in rows]

    def get_monthly_medians(self) -> list[dict]:
        """Median price per month for trend charts."""
        rows = self.conn.execute("""
            SELECT
                strftime('%Y-%m', sale_date) as month,
                COUNT(*) as count,
                AVG(sale_price) as avg_price
            FROM auction_results
            WHERE sale_price IS NOT NULL
            GROUP BY month
            ORDER BY month
        """).fetchall()
        return [dict(r) for r in rows]

    def close(self):
        self.conn.close()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd auction-tracker && python -m pytest tests/test_database.py -v`
Expected: All 7 tests PASS

- [ ] **Step 5: Commit**

```bash
cd auction-tracker && git add auction_tracker/database.py tests/test_database.py && git commit -m "feat: add SQLite database layer with insert, query, and stats"
```

---

### Task 4: Base Scraper

**Files:**
- Create: `auction-tracker/auction_tracker/scraper/__init__.py`
- Create: `auction-tracker/auction_tracker/scraper/base.py`

- [ ] **Step 1: Create scraper package init**

```python
"""Web scrapers for real estate agency auction results."""
from auction_tracker.scraper.base import BaseScraper

__all__ = ["BaseScraper"]
```

- [ ] **Step 2: Implement base.py**

```python
"""Base scraper class with shared Playwright logic."""
import random
import time
import logging
from abc import ABC, abstractmethod
from playwright.sync_api import sync_playwright, Page, Browser

from auction_tracker.models import AuctionResult

logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    """Abstract base for agency scrapers.

    Subclasses set `agency_name` and implement `extract_results(page) -> list[AuctionResult]`.
    """

    agency_name: str
    base_url: str

    def scrape(self) -> list[AuctionResult]:
        """Run the full scrape flow. Returns list of parsed results."""
        results = []
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            try:
                page.goto(self.base_url, timeout=30_000)
                self._wait_for_content(page)
                results = self.extract_results(page)
            except Exception as e:
                logger.error(f"{self.agency_name}: scrape failed — {e}")
                raise
            finally:
                browser.close()
        return results

    def _wait_for_content(self, page: Page):
        """Wait for dynamic content to load. Override if needed."""
        page.wait_for_load_state("networkidle", timeout=15_000)
        time.sleep(2)

    def _random_delay(self, min_s: float = 0.5, max_s: float = 2.0):
        time.sleep(random.uniform(min_s, max_s))

    @abstractmethod
    def extract_results(self, page: Page) -> list[AuctionResult]:
        """Parse the rendered page and return results."""
        ...

    @staticmethod
    def _clean_price(text: str) -> float | None:
        """Parse price strings like '$850,000' or 'TBC' into float or None."""
        if not text:
            return None
        cleaned = text.replace("$", "").replace(",", "").strip()
        try:
            return float(cleaned)
        except ValueError:
            return None

    @staticmethod
    def _clean_int(text: str) -> int | None:
        """Parse a string into an int, returning None on failure."""
        if not text:
            return None
        try:
            return int(text.strip())
        except ValueError:
            return None
```

- [ ] **Step 3: Commit**

```bash
cd auction-tracker && git add auction_tracker/scraper/ && git commit -m "feat: add BaseScraper with Playwright scaffolding"
```

---

### Task 5: Holmwood Scraper

**Files:**
- Create: `auction-tracker/auction_tracker/scraper/holmwood.py`
- Create: `auction-tracker/tests/fixtures/holmwood_sample.html` (saved during research step)
- Modify: `auction-tracker/tests/test_parsing.py` (create with Holmwood tests)

**Note:** Holmwood's site (`holmwood.co.nz/recent-sales/`) loads results via JavaScript. The exact CSS selectors will be determined in Step 1 by rendering the page with Playwright and inspecting the DOM. The test and implementation below use a discoverable pattern — concrete selectors are filled in after the research step.

- [ ] **Step 1: Research — render the page and save a snapshot**

Run this script to open the page, wait for content, and save the rendered HTML:

```python
# save as: scripts/snapshot_holmwood.py
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto("https://www.holmwood.co.nz/recent-sales/", timeout=30_000)
    page.wait_for_load_state("networkidle", timeout=15_000)
    page.wait_for_timeout(3000)  # extra wait for JS rendering
    html = page.content()
    with open("tests/fixtures/holmwood_sample.html", "w") as f:
        f.write(html)
    # Print the first few property elements to discover selectors
    # Look for listing cards/rows in the rendered HTML
    print("Page title:", page.title())
    # Try common selectors for property listings
    selectors_to_try = [
        ".property-card", ".listing-card", ".result-item",
        "[class*='property']", "[class*='listing']", "[class*='result']",
        "article", ".card", ".tile",
    ]
    for sel in selectors_to_try:
        count = page.locator(sel).count()
        if count > 0:
            print(f"Found {count} elements matching '{sel}'")
    browser.close()
```

Run: `cd auction-tracker && python scripts/snapshot_holmwood.py`

- [ ] **Step 2: Write parsing test against the saved snapshot**

After discovering the actual selectors, write the test. The pattern below assumes selectors are discovered — update `PROPERTY_SELECTOR` and extraction logic based on Step 1 findings:

```python
"""Tests for scraper parsing logic."""
import pytest
from pathlib import Path
from auction_tracker.scraper.holmwood import HolmwoodScraper

FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> str:
    return (FIXTURES / name).read_text()


class TestHolmwoodScraper:
    def test_parse_results_from_html(self, monkeypatch):
        """Parse properties from a saved HTML snapshot."""
        html = load_fixture("holmwood_sample.html")
        scraper = HolmwoodScraper()

        # Mock the Playwright page to return our saved HTML
        class MockLocator:
            def __init__(self, html):
                self.html = html

            def inner_html(self):
                return self.html

        class MockPage:
            def content(self):
                return html

            def locator(self, selector):
                # Return a mock that has the right HTML
                return MockLocator(html)

            def query_selector_all(self, selector):
                # Use BeautifulSoup on the saved HTML
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(html, "html.parser")
                return soup.select(selector)

        results = scraper.extract_results(MockPage())
        assert len(results) > 0

        for r in results:
            assert r.address
            assert r.suburb
            assert r.agency == "Holmwood"
            assert r.sale_date is not None

    def test_price_parsing(self):
        assert HolmwoodScraper._clean_price("$850,000") == 850_000
        assert HolmwoodScraper._clean_price("TBC") is None
        assert HolmwoodScraper._clean_price("Auction") is None
        assert HolmwoodScraper._clean_price("") is None
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd auction-tracker && python -m pytest tests/test_parsing.py -v`
Expected: FAIL — `HolmwoodScraper` not defined

- [ ] **Step 4: Implement Holmwood scraper**

```python
"""Holmwood real estate scraper."""
import re
import logging
from datetime import date
from playwright.sync_api import Page
from bs4 import BeautifulSoup

from auction_tracker.models import AuctionResult
from auction_tracker.scraper.base import BaseScraper

logger = logging.getLogger(__name__)


class HolmwoodScraper(BaseScraper):
    agency_name = "Holmwood"
    base_url = "https://www.holmwood.co.nz/recent-sales/"

    def extract_results(self, page: Page) -> list[AuctionResult]:
        """Parse the rendered recent-sales page."""
        html = page.content()
        soup = BeautifulSoup(html, "html.parser")
        results = []

        # Selector determined from Step 1 research — update based on findings.
        # Common patterns on NZ real estate sites: cards with class containing 'property' or 'listing'
        cards = soup.select("[class*='property'], [class*='listing'], [class*='result']")

        # If the broad selector above captures too much, narrow to actual property cards.
        # Typical structure: each card contains an address heading, price text, and detail list.
        for card in cards:
            try:
                result = self._parse_card(card)
                if result:
                    results.append(result)
            except Exception as e:
                logger.warning(f"Holmwood: failed to parse card — {e}")
                continue

        return results

    def _parse_card(self, card) -> AuctionResult | None:
        """Parse a single property card. Selectors refined after Step 1 research."""

        # Address: typically an <h2>, <h3>, or <a> with the street address
        address_el = card.select_one("h2, h3, h4, .address, .title, a[href*='property']")
        if not address_el:
            return None
        address = address_el.get_text(strip=True)

        # Suburb: extract from address string (e.g., "12 Example St, Riccarton")
        parts = [p.strip() for p in address.split(",")]
        suburb = parts[-1] if len(parts) > 1 else "Unknown"
        street = parts[0] if len(parts) > 0 else address

        # Price: look for text containing "$" or "Sold"
        price_el = card.select_one("[class*='price'], .sold-price, .result-price")
        price_text = price_el.get_text(strip=True) if price_el else None
        sale_price = self._clean_price(price_text) if price_text else None

        # Date: look for date pattern in text
        date_text = card.get_text()
        sale_date = self._extract_date(date_text)

        # Bedrooms / Bathrooms: look for icon+digit patterns
        beds = self._extract_bedrooms(card)
        baths = self._extract_bathrooms(card)

        # Source URL
        link = card.select_one("a[href]")
        source_url = link.get("href", "") if link else ""
        if source_url and not source_url.startswith("http"):
            source_url = "https://www.holmwood.co.nz" + source_url

        return AuctionResult(
            address=street,
            suburb=suburb,
            sale_price=sale_price,
            sale_date=sale_date,
            agency=self.agency_name,
            bedrooms=beds,
            bathrooms=baths,
            source_url=source_url,
        )

    def _extract_date(self, text: str) -> date | None:
        """Extract a date from text like 'Sold 15 May 2026' or '15/05/2026'."""
        # Pattern: "Sold 15 May 2026" or "15 May 2026"
        months = {
            "january": 1, "february": 2, "march": 3, "april": 4,
            "may": 5, "june": 6, "july": 7, "august": 8,
            "september": 9, "october": 10, "november": 11, "december": 12,
            "jan": 1, "feb": 2, "mar": 3, "apr": 4, "jun": 6,
            "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
        }
        pattern = r"(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{4})"
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            day = int(match.group(1))
            month = months[match.group(2).lower()]
            year = int(match.group(3))
            return date(year, month, day)

        # Pattern: dd/mm/yyyy
        match = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", text)
        if match:
            return date(int(match.group(3)), int(match.group(2)), int(match.group(1)))

        return None

    def _extract_bedrooms(self, card) -> int | None:
        """Find bedroom count near a bed icon or label."""
        text = card.get_text()
        match = re.search(r"(\d+)\s*(?:bed|bedroom|bdr)", text, re.IGNORECASE)
        if match:
            return int(match.group(1))
        return None

    def _extract_bathrooms(self, card) -> int | None:
        """Find bathroom count near a bath icon or label."""
        text = card.get_text()
        match = re.search(r"(\d+)\s*(?:bath|bathroom|bth)", text, re.IGNORECASE)
        if match:
            return int(match.group(1))
        return None
```

- [ ] **Step 5: Run tests**

Run: `cd auction-tracker && python -m pytest tests/test_parsing.py -v`
Expected: Tests PASS after selectors are refined from Step 1

- [ ] **Step 6: Commit**

```bash
cd auction-tracker && git add auction_tracker/scraper/holmwood.py tests/test_parsing.py tests/fixtures/holmwood_sample.html && git commit -m "feat: add Holmwood scraper with snapshot-based test"
```

---

### Task 6: Grenadier Scraper

**Files:**
- Create: `auction-tracker/auction_tracker/scraper/grenadier.py`
- Create: `auction-tracker/tests/fixtures/grenadier_sample.html` (saved during research step)
- Modify: `auction-tracker/tests/test_parsing.py` (add Grenadier test class)

- [ ] **Step 1: Research — render the page and save a snapshot**

Grenadier returned HTTP 403 to a basic request — Playwright with a real browser user-agent should bypass this.

```python
# save as: scripts/snapshot_grenadier.py
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto("https://grenadier.co.nz/sold-properties/", timeout=30_000)
    page.wait_for_load_state("networkidle", timeout=15_000)
    page.wait_for_timeout(3000)
    html = page.content()
    with open("tests/fixtures/grenadier_sample.html", "w") as f:
        f.write(html)
    print("Page title:", page.title())
    selectors_to_try = [
        ".property-card", ".listing-card", ".result-item", ".sold-property",
        "[class*='property']", "[class*='listing']", "[class*='result']",
        "[class*='sold']", "article", ".card", ".tile",
    ]
    for sel in selectors_to_try:
        count = page.locator(sel).count()
        if count > 0:
            print(f"Found {count} elements matching '{sel}'")
    browser.close()
```

Run: `cd auction-tracker && python scripts/snapshot_grenadier.py`

- [ ] **Step 2: Add Grenadier tests to test_parsing.py**

```python
class TestGrenadierScraper:
    def test_parse_results_from_html(self, monkeypatch):
        html = load_fixture("grenadier_sample.html")
        scraper = GrenadierScraper()

        class MockPage:
            def content(self):
                return html

        results = scraper.extract_results(MockPage())
        assert len(results) > 0

        for r in results:
            assert r.address
            assert r.agency == "Grenadier"
            assert r.sale_date is not None
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd auction-tracker && python -m pytest tests/test_parsing.py::TestGrenadierScraper -v`
Expected: FAIL — `GrenadierScraper` not defined

- [ ] **Step 4: Implement Grenadier scraper**

```python
"""Grenadier real estate scraper."""
import re
import logging
from datetime import date
from playwright.sync_api import Page
from bs4 import BeautifulSoup

from auction_tracker.models import AuctionResult
from auction_tracker.scraper.base import BaseScraper

logger = logging.getLogger(__name__)


class GrenadierScraper(BaseScraper):
    agency_name = "Grenadier"
    base_url = "https://grenadier.co.nz/sold-properties/"

    def extract_results(self, page: Page) -> list[AuctionResult]:
        html = page.content()
        soup = BeautifulSoup(html, "html.parser")
        results = []

        # Selectors refined after Step 1 research
        cards = soup.select("[class*='property'], [class*='listing'], [class*='sold'], [class*='result']")

        for card in cards:
            try:
                result = self._parse_card(card)
                if result:
                    results.append(result)
            except Exception as e:
                logger.warning(f"Grenadier: failed to parse card — {e}")
                continue

        return results

    def _parse_card(self, card) -> AuctionResult | None:
        address_el = card.select_one("h2, h3, h4, .address, .title, a[href*='property']")
        if not address_el:
            return None
        address = address_el.get_text(strip=True)

        parts = [p.strip() for p in address.split(",")]
        suburb = parts[-1] if len(parts) > 1 else "Unknown"
        street = parts[0] if len(parts) > 0 else address

        price_el = card.select_one("[class*='price'], .sold-price, .result-price")
        price_text = price_el.get_text(strip=True) if price_el else None
        sale_price = self._clean_price(price_text) if price_text else None

        date_text = card.get_text()
        sale_date = self._extract_date(date_text)

        beds = self._extract_bedrooms(card)
        baths = self._extract_bathrooms(card)

        link = card.select_one("a[href]")
        source_url = link.get("href", "") if link else ""
        if source_url and not source_url.startswith("http"):
            source_url = "https://grenadier.co.nz" + source_url

        return AuctionResult(
            address=street,
            suburb=suburb,
            sale_price=sale_price,
            sale_date=sale_date,
            agency=self.agency_name,
            bedrooms=beds,
            bathrooms=baths,
            source_url=source_url,
        )

    def _extract_date(self, text: str) -> date | None:
        months = {
            "january": 1, "february": 2, "march": 3, "april": 4,
            "may": 5, "june": 6, "july": 7, "august": 8,
            "september": 9, "october": 10, "november": 11, "december": 12,
            "jan": 1, "feb": 2, "mar": 3, "apr": 4, "jun": 6,
            "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
        }
        pattern = r"(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{4})"
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return date(int(match.group(3)), months[match.group(2).lower()], int(match.group(1)))
        match = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", text)
        if match:
            return date(int(match.group(3)), int(match.group(2)), int(match.group(1)))
        return None

    def _extract_bedrooms(self, card) -> int | None:
        text = card.get_text()
        match = re.search(r"(\d+)\s*(?:bed|bedroom|bdr)", text, re.IGNORECASE)
        return int(match.group(1)) if match else None

    def _extract_bathrooms(self, card) -> int | None:
        text = card.get_text()
        match = re.search(r"(\d+)\s*(?:bath|bathroom|bth)", text, re.IGNORECASE)
        return int(match.group(1)) if match else None
```

- [ ] **Step 5: Run tests**

Run: `cd auction-tracker && python -m pytest tests/test_parsing.py -v`
Expected: All tests PASS after selectors refined from Step 1

- [ ] **Step 6: Commit**

```bash
cd auction-tracker && git add auction_tracker/scraper/grenadier.py tests/test_parsing.py tests/fixtures/grenadier_sample.html && git commit -m "feat: add Grenadier scraper with snapshot-based test"
```

---

### Task 7: CLI Commands

**Files:**
- Create: `auction-tracker/auction_tracker/cli.py`

- [ ] **Step 1: Implement CLI**

```python
"""CLI entry point for auction-tracker."""
import logging
import click

from auction_tracker.database import Database
from auction_tracker.models import ScrapeReport
from auction_tracker.scraper.holmwood import HolmwoodScraper
from auction_tracker.scraper.grenadier import GrenadierScraper

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

SCRAPERS = [HolmwoodScraper, GrenadierScraper]


@click.group()
def main():
    """Christchurch Auction Results Tracker."""


@main.command()
def scrape():
    """Scrape auction results from all agencies."""
    db = Database()
    agency_results = {}
    errors = {}

    for scraper_cls in SCRAPERS:
        scraper = scraper_cls()
        try:
            results = scraper.scrape()
            count = 0
            for r in results:
                count += db.insert(r)
            agency_results[scraper.agency_name] = count
            logger.info(f"{scraper.agency_name}: {count} new results")
        except Exception as e:
            errors[scraper.agency_name] = str(e)
            logger.error(f"{scraper.agency_name}: FAILED — {e}")

    db.close()
    report = ScrapeReport(agency_results, errors)

    if errors:
        logger.info(f"\n{len(errors)} agency(s) failed: {', '.join(errors.keys())}")

    if report.all_failed:
        logger.error("All scrapers failed.")
        raise SystemExit(1)

    logger.info(f"Done. {report.total_new} new results total.")


@main.command()
def view():
    """Launch the Streamlit dashboard."""
    import subprocess
    import sys
    from pathlib import Path

    dashboard_path = Path(__file__).parent / "dashboard.py"
    subprocess.run([sys.executable, "-m", "streamlit", "run", str(dashboard_path)])


@main.command()
def stats():
    """Print a quick summary of the database."""
    db = Database()
    s = db.get_stats()
    click.echo(f"Total sales tracked: {s['total']}")
    click.echo(f"Sales with prices:  {s['with_price']}")
    if s["median_price"]:
        click.echo(f"Median sale price:  ${s['median_price']:,.0f}")
        click.echo(f"Average sale price: ${s['avg_price']:,.0f}")
        click.echo(f"Lowest sale:        ${s['min_price']:,.0f}")
        click.echo(f"Highest sale:       ${s['max_price']:,.0f}")

    last = db.get_last_scrape_per_agency()
    if last:
        click.echo("\nLast scrape per agency:")
        for agency, ts in last.items():
            click.echo(f"  {agency}: {ts}")

    db.close()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verify CLI loads correctly**

Run: `cd auction-tracker && python -m auction_tracker.cli --help`
Expected: Shows help with `scrape`, `view`, `stats` commands

- [ ] **Step 3: Commit**

```bash
cd auction-tracker && git add auction_tracker/cli.py && git commit -m "feat: add CLI with scrape, view, and stats commands"
```

---

### Task 8: Streamlit Dashboard

**Files:**
- Create: `auction-tracker/auction_tracker/dashboard.py`

- [ ] **Step 1: Implement dashboard**

```python
"""Streamlit dashboard for auction results."""
import streamlit as st
import pandas as pd
from auction_tracker.database import Database

st.set_page_config(page_title="CHCH Auction Tracker", layout="wide")
st.title("Christchurch Auction Results")

db = Database()


def overview_tab():
    st.header("Overview")
    stats = db.get_stats()

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Sales", stats["total"])
    with col2:
        median = f"${stats['median_price']:,.0f}" if stats["median_price"] else "N/A"
        st.metric("Median Price", median)
    with col3:
        avg = f"${stats['avg_price']:,.0f}" if stats["avg_price"] else "N/A"
        st.metric("Average Price", avg)
    with col4:
        price_range = (
            f"${stats['min_price']:,.0f} – ${stats['max_price']:,.0f}"
            if stats["min_price"] and stats["max_price"]
            else "N/A"
        )
        st.metric("Price Range", price_range)

    st.subheader("Last Scrape per Agency")
    last = db.get_last_scrape_per_agency()
    if last:
        df_last = pd.DataFrame(
            [{"Agency": k, "Last Scraped": v} for k, v in last.items()]
        )
        st.dataframe(df_last, use_container_width=True)
    else:
        st.write("No data yet. Run `auction-tracker scrape` to collect results.")


def trends_tab():
    st.header("Price Trends")

    monthly = db.get_monthly_medians()
    if not monthly:
        st.write("Not enough data for trends yet.")
        return

    df = pd.DataFrame(monthly)
    df["month"] = pd.to_datetime(df["month"])

    st.subheader("Median Sale Price Over Time")
    st.line_chart(df.set_index("month")["avg_price"])

    st.subheader("Number of Sales Over Time")
    st.bar_chart(df.set_index("month")["count"])

    st.subheader("Filter by Suburb")
    suburbs = db.get_all_suburbs()
    if suburbs:
        selected = st.selectbox("Suburb", ["All"] + suburbs)
        if selected != "All":
            rows = db.get_by_suburb(selected)
            suburb_df = pd.DataFrame(rows)
            if not suburb_df.empty and "sale_price" in suburb_df.columns:
                st.line_chart(
                    suburb_df.set_index("sale_date")["sale_price"]
                )


def explore_tab():
    st.header("Explore Results")

    suburbs = ["All"] + db.get_all_suburbs()
    selected_suburb = st.selectbox("Suburb", suburbs, key="explore_suburb")

    min_price = st.number_input("Min Price", value=0, step=50_000)
    max_price = st.number_input("Max Price", value=5_000_000, step=50_000)

    rows = db.get_all()
    df = pd.DataFrame(rows)

    if df.empty:
        st.write("No results yet.")
        return

    # Filter
    if selected_suburb != "All":
        df = df[df["suburb"] == selected_suburb]
    if "sale_price" in df.columns:
        df = df[
            (df["sale_price"].isna()) | ((df["sale_price"] >= min_price) & (df["sale_price"] <= max_price))
        ]

    st.dataframe(
        df[["address", "suburb", "sale_price", "sale_date", "agency", "bedrooms", "bathrooms"]],
        use_container_width=True,
    )

    st.subheader("Median Price by Suburb")
    if "sale_price" in df.columns and "suburb" in df.columns:
        by_suburb = (
            df[df["sale_price"].notna()]
            .groupby("suburb")["sale_price"]
            .median()
            .sort_values(ascending=False)
            .head(15)
        )
        st.bar_chart(by_suburb)


tab1, tab2, tab3 = st.tabs(["Overview", "Trends", "Explore"])
with tab1:
    overview_tab()
with tab2:
    trends_tab()
with tab3:
    explore_tab()

db.close()
```

- [ ] **Step 2: Verify dashboard imports correctly**

Run: `cd auction-tracker && python -c "from auction_tracker.dashboard import tab1; print('OK')"`
Expected: "OK" (Streamlit might produce a warning about no running server, that's fine)

- [ ] **Step 3: Commit**

```bash
cd auction-tracker && git add auction_tracker/dashboard.py && git commit -m "feat: add Streamlit dashboard with Overview, Trends, and Explore tabs"
```

---

### Task 9: Integration Test — End-to-End Scrape Flow

**Files:**
- Create: `auction-tracker/tests/test_integration.py`

- [ ] **Step 1: Write integration test**

```python
"""End-to-end integration tests."""
import pytest
from datetime import date
from auction_tracker.database import Database
from auction_tracker.models import AuctionResult, ScrapeReport


class TestEndToEnd:
    def test_full_pipeline(self):
        """Simulate a complete scrape → store → query pipeline."""
        db = Database(":memory:")

        # Simulate scraped results from two agencies
        holmwood_results = [
            AuctionResult(
                address="12 Example St", suburb="Riccarton",
                sale_price=850_000, sale_date=date(2026, 5, 15),
                agency="Holmwood", bedrooms=3, bathrooms=1,
                source_url="https://holmwood.co.nz/listing/1",
            ),
            AuctionResult(
                address="45 Test Rd", suburb="Ilam",
                sale_price=920_000, sale_date=date(2026, 5, 20),
                agency="Holmwood", bedrooms=4, bathrooms=2,
                source_url="https://holmwood.co.nz/listing/2",
            ),
        ]
        grenadier_results = [
            AuctionResult(
                address="78 Sample Ave", suburb="Riccarton",
                sale_price=780_000, sale_date=date(2026, 5, 18),
                agency="Grenadier", bedrooms=3, bathrooms=1,
                source_url="https://grenadier.co.nz/listing/3",
            ),
        ]

        # Simulate scrape report logic
        agency_results = {}
        errors = {}
        for results in [holmwood_results, grenadier_results]:
            for r in results:
                count = db.insert(r)
                agency_results[r.agency] = agency_results.get(r.agency, 0) + count

        report = ScrapeReport(agency_results, errors)

        assert report.all_failed is False
        assert report.total_new == 3

        # Verify data in DB
        stats = db.get_stats()
        assert stats["total"] == 3
        assert stats["median_price"] == 850_000

        # Verify suburb filtering
        riccarton = db.get_by_suburb("Riccarton")
        assert len(riccarton) == 2

        # Monthly trend
        monthly = db.get_monthly_medians()
        assert len(monthly) == 1
        assert monthly[0]["count"] == 3

        db.close()

    def test_partial_scraper_failure(self):
        """Verify ScrapeReport handles partial failures correctly."""
        report = ScrapeReport(
            agency_results={"Holmwood": 5},
            errors={"Grenadier": "Connection timeout"},
        )
        assert report.all_failed is False
        assert report.total_new == 5

    def test_all_scrapers_failed(self):
        """SystemExit(1) should be raised only when all scrapers fail."""
        report = ScrapeReport(
            agency_results={},
            errors={"Holmwood": "Timeout", "Grenadier": "404"},
        )
        assert report.all_failed is True
        assert report.total_new == 0

    def test_no_new_results(self):
        """Zero results for all agencies is not an error."""
        report = ScrapeReport(
            agency_results={"Holmwood": 0, "Grenadier": 0},
            errors={},
        )
        assert report.all_failed is False
```

- [ ] **Step 2: Run integration tests**

Run: `cd auction-tracker && python -m pytest tests/test_integration.py -v`
Expected: All 4 integration tests PASS

- [ ] **Step 3: Commit**

```bash
cd auction-tracker && git add tests/test_integration.py && git commit -m "test: add integration tests for scrape → store → query pipeline"
```

---

### Task 10: Run Full Test Suite and Final Wiring

- [ ] **Step 1: Run the complete test suite**

Run: `cd auction-tracker && python -m pytest -v`
Expected: All tests PASS (models, database, parsing, integration)

- [ ] **Step 2: Verify CLI entry point works via pyproject.toml**

Run: `cd auction-tracker && pip install -e . && auction-tracker --help`
Expected: Shows CLI help with scrape, view, stats

- [ ] **Step 3: Run `auction-tracker stats` against an empty DB**

Run: `cd auction-tracker && auction-tracker stats`
Expected: "Total sales tracked: 0" (non-error output)

- [ ] **Step 4: Commit any remaining changes**

```bash
cd auction-tracker && git add -A && git commit -m "chore: final wiring and verification"
```
