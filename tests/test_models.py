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
