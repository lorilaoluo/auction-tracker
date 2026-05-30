"""Holmwood scraper — uses AuctionsLive API."""
import logging
from datetime import datetime, timezone, date
import requests

from auction_tracker.models import AuctionResult
from auction_tracker.scraper.base import BaseScraper

logger = logging.getLogger(__name__)

API_URL = "https://widget.auctionslive.com/widget/v3/Pqn/auctions"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "application/json",
}


class HolmwoodScraper(BaseScraper):
    agency_name = "Holmwood"

    def scrape(self) -> list[AuctionResult]:
        """Fetch all pages of past auction results from the AuctionsLive API."""
        results = []
        page = 1
        base_url = f"{API_URL}?page={{}}&time_filter=past&auction_type[]=null&filters"

        while True:
            url = base_url.format(page)
            logger.info(f"Fetching {url}")
            resp = requests.get(url, headers=HEADERS, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            parsed = self._parse_response(data)
            results.extend(parsed)

            next_page = data.get("nextPageUrl")
            if not next_page:
                break
            page += 1

        return results

    def _parse_response(self, data: dict) -> list[AuctionResult]:
        results = []
        for prop in data.get("properties", []):
            try:
                result = self._parse_property(prop)
                if result:
                    results.append(result)
            except Exception as e:
                logger.warning(f"Holmwood: failed to parse property {prop.get('id')} — {e}")
                continue
        return results

    def _parse_property(self, prop: dict) -> AuctionResult | None:
        status = prop.get("status")
        if status != 1:
            return None  # Only include SOLD properties with confirmed prices

        sold_price = prop.get("soldPrice")
        if not sold_price or sold_price == 0:
            return None

        display_address = prop.get("displayAddress", "")
        suburb = self._extract_suburb(display_address)

        auction_dt = prop.get("auctionDateTime")
        sale_date = None
        if auction_dt:
            try:
                sale_date = datetime.fromisoformat(
                    auction_dt.replace("Z", "+00:00")
                ).date()
            except (ValueError, TypeError):
                pass

        detail = prop.get("propertyDetail") or {}
        beds = detail.get("bedrooms")
        baths = detail.get("bathrooms")
        property_type = detail.get("propertyType")

        prop_id = prop.get("id")
        source_url = f"https://widget.auctionslive.com/widget/past_auctions/Pqn?src=widgetiframe&auction_type=null#lot-{prop_id}"

        return AuctionResult(
            address=self._extract_street(display_address),
            suburb=suburb,
            sale_price=float(sold_price),
            sale_date=sale_date or date.today(),
            agency=self.agency_name,
            bedrooms=int(beds) if beds else None,
            bathrooms=int(baths) if baths else None,
            property_type=property_type,
            source_url=source_url,
        )

    @staticmethod
    def _extract_suburb(display_address: str) -> str:
        """Extract suburb from '123 Street, Suburb' format."""
        parts = [p.strip() for p in display_address.split(",")]
        return parts[-1] if len(parts) > 1 else "Unknown"

    @staticmethod
    def _extract_street(display_address: str) -> str:
        """Extract street address from '123 Street, Suburb' format."""
        parts = [p.strip() for p in display_address.split(",")]
        return parts[0] if len(parts) > 0 else display_address
