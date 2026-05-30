"""Grenadier scraper for auction results."""
import re
import logging
from datetime import date, timedelta
from playwright.sync_api import sync_playwright, Page
from bs4 import BeautifulSoup

from auction_tracker.models import AuctionResult
from auction_tracker.scraper.base import BaseScraper

logger = logging.getLogger(__name__)

MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
}


class GrenadierScraper(BaseScraper):
    agency_name = "Grenadier"
    url = "https://grenadier.co.nz/auction-results/"

    def scrape(self, lookback_days: int | None = None) -> list[AuctionResult]:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080},
                locale="en-NZ",
            )
            page = context.new_page()
            try:
                page.goto(self.url, timeout=30_000)
                page.wait_for_load_state("networkidle", timeout=15_000)
                page.wait_for_timeout(3000)
                sold_cutoff = date.today() - timedelta(days=lookback_days) if lookback_days else None
                passed_in_cutoff = date.today() - timedelta(days=30)
                return self.extract_results(page, sold_cutoff, passed_in_cutoff)
            except Exception as e:
                logger.error(f"Grenadier: scrape failed — {e}")
                raise
            finally:
                browser.close()

    def extract_results(self, page: Page, sold_cutoff: date | None = None, passed_in_cutoff: date | None = None) -> list[AuctionResult]:
        html = page.content()
        soup = BeautifulSoup(html, "html.parser")
        results = []

        # Stop when past the more permissive cutoff
        stop_cutoff = passed_in_cutoff
        if sold_cutoff and (passed_in_cutoff is None or sold_cutoff < passed_in_cutoff):
            stop_cutoff = sold_cutoff

        for container in soup.select(".result-container"):
            date_header = container.select_one("h3")
            sale_date = self._parse_date(date_header.get_text(strip=True)) if date_header else None

            # Stop if this container's date is older than the stop cutoff
            if stop_cutoff and sale_date and sale_date < stop_cutoff:
                break

            for row in container.select("tbody tr"):
                try:
                    result = self._parse_row(row, sale_date, sold_cutoff, passed_in_cutoff)
                    if result:
                        results.append(result)
                except Exception as e:
                    logger.warning(f"Grenadier: failed to parse row — {e}")
                    continue

        return results

    def _parse_row(self, row, sale_date: date | None, sold_cutoff: date | None = None, passed_in_cutoff: date | None = None) -> AuctionResult | None:
        cells = row.select("td")
        if len(cells) < 4:
            return None

        address_text = cells[1].get_text(strip=True)
        status_text = cells[3].get_text(strip=True)

        status_upper = status_text.upper()
        if status_upper.startswith("SOLD"):
            sale_price = self._extract_price(status_text)
            if sale_price is None:
                return None
            if sold_cutoff and sale_date and sale_date < sold_cutoff:
                return None
        elif status_upper.startswith("PASSED"):
            sale_price = None
            if passed_in_cutoff and sale_date and sale_date < passed_in_cutoff:
                return None
        else:
            return None

        street, suburb = self._parse_address(address_text)

        source_url = self.url

        return AuctionResult(
            address=street,
            suburb=suburb,
            sale_price=sale_price,
            sale_date=sale_date or date.today(),
            agency=self.agency_name,
            source_url=source_url,
        )

    @staticmethod
    def _parse_address(address_text: str) -> tuple[str, str]:
        """Split '123 Street, Suburb, NZ 8052' into (street, suburb)."""
        parts = [p.strip() for p in address_text.split(",")]
        street = parts[0] if len(parts) > 0 else address_text
        # Suburb is the second part (skip postcode like "NZ 8052")
        suburb = parts[1].strip() if len(parts) > 1 else "Unknown"
        # Remove postcode from suburb if present (e.g., "NZ 8052" pattern)
        suburb = re.sub(r"\s*(?:NZ|RD)\s*\d*$", "", suburb).strip()
        return street, suburb

    @staticmethod
    def _extract_price(status_text: str) -> float | None:
        """Extract price from 'SOLD $881,500' format."""
        match = re.search(r"\$([\d,]+(?:\.\d+)?)", status_text)
        if match:
            return float(match.group(1).replace(",", ""))
        return None

    @staticmethod
    def _parse_date(text: str) -> date | None:
        """Parse 'Thursday, 28 May 2026' into a date."""
        pattern = r"(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})"
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            day = int(match.group(1))
            month = MONTHS[match.group(2).lower()]
            year = int(match.group(3))
            return date(year, month, day)
        return None
