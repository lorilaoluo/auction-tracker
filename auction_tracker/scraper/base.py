"""Base scraper class with shared Playwright logic."""
import random
import time
import logging
from abc import ABC, abstractmethod
from playwright.sync_api import sync_playwright, Page

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
