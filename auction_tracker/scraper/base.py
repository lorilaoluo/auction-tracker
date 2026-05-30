"""Base scraper class."""
import logging
from abc import ABC, abstractmethod

from auction_tracker.models import AuctionResult

logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    """Abstract base for agency scrapers.

    Subclasses set `agency_name` and implement `scrape() -> list[AuctionResult]`.
    """

    agency_name: str

    @abstractmethod
    def scrape(self, lookback_days: int | None = None) -> list[AuctionResult]:
        """Run the full scrape flow. Returns list of parsed results.

        Args:
            lookback_days: Only return results from this many days ago.
                           None means fetch everything.
        """
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
