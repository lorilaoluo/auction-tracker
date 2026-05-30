"""End-to-end integration tests."""
import pytest
from datetime import date
from auction_tracker.database import Database
from auction_tracker.models import AuctionResult, ScrapeReport


class TestEndToEnd:
    def test_full_pipeline(self):
        """Simulate a complete scrape → store → query pipeline."""
        db = Database(":memory:")

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

        agency_results = {}
        errors = {}
        for results in [holmwood_results, grenadier_results]:
            for r in results:
                count = db.insert(r)
                agency_results[r.agency] = agency_results.get(r.agency, 0) + count

        report = ScrapeReport(agency_results, errors)

        assert report.all_failed is False
        assert report.total_new == 3

        stats = db.get_stats()
        assert stats["total"] == 3
        assert stats["median_price"] == 850_000

        riccarton = db.get_by_suburb("Riccarton")
        assert len(riccarton) == 2

        monthly = db.get_monthly_medians()
        assert len(monthly) == 1
        assert monthly[0]["total"] == 3
        assert monthly[0]["sold"] == 3
        assert monthly[0]["passed_in"] == 0

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
