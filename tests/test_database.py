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

    def test_null_price_not_treated_as_duplicate(self, db):
        """SQLite treats NULLs as distinct in UNIQUE constraints.
        Two same-address+date listings with undisclosed prices may be different properties."""
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
        assert db.insert(r2) == 1  # NULL prices are distinct in SQL
        assert len(db.get_all()) == 2

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
