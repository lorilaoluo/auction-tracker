"""Tests for scraper parsing logic."""
import json
import pytest
from pathlib import Path
from datetime import date
from unittest.mock import patch, Mock
from auction_tracker.scraper.holmwood import HolmwoodScraper

FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> str:
    return (FIXTURES / name).read_text()


class TestHolmwoodScraper:
    def test_parse_results_from_api(self):
        """Parse properties from a saved API response."""
        raw = load_fixture("holmwood_sample.json")
        data = json.loads(raw)
        scraper = HolmwoodScraper()

        results = scraper._parse_response(data)
        assert len(results) > 0

        for r in results:
            assert r.address
            assert r.agency == "Holmwood"
            assert r.source_url

    def test_only_sold_properties_extracted(self):
        """Only status=1 (SOLD) properties should be included."""
        raw = load_fixture("holmwood_sample.json")
        data = json.loads(raw)
        scraper = HolmwoodScraper()

        results = scraper._parse_response(data)
        # In the fixture: 2 SOLD (status=1), 3 Passed In (status=4), 1 Withdrawn & Sold (status=13)
        assert len(results) == 2

        for r in results:
            assert r.sale_price is not None
            assert r.sale_price > 0

    def test_price_parsing(self):
        assert HolmwoodScraper._clean_price("$850,000") == 850_000
        assert HolmwoodScraper._clean_price("TBC") is None
        assert HolmwoodScraper._clean_price("Auction") is None
        assert HolmwoodScraper._clean_price("") is None

    def test_suburb_extraction(self):
        """Suburb should be extracted from displayAddress."""
        assert HolmwoodScraper._extract_suburb("18 Burkett Street, Marshland") == "Marshland"
        assert HolmwoodScraper._extract_suburb("5 Wildberry Street, Woolston") == "Woolston"
        assert HolmwoodScraper._extract_suburb("Unknown") == "Unknown"

    @patch("auction_tracker.scraper.holmwood.requests.get")
    def test_scrape_integration(self, mock_get):
        """Full scrape flow with mocked API."""
        with open(FIXTURES / "holmwood_sample.json") as f:
            mock_data = json.load(f)

        mock_data.pop("nextPageUrl", None)  # prevent infinite loop

        mock_response = Mock()
        mock_response.json.return_value = mock_data
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        scraper = HolmwoodScraper()
        results = scraper.scrape()

        assert len(results) == 2
        assert results[0].agency == "Holmwood"
