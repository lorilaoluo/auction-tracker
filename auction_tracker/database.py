"""SQLite database layer for auction results."""
import sqlite3
from datetime import datetime
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
            before = self.conn.total_changes
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
            return self.conn.total_changes - before
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
        """Monthly avg price for trend charts."""
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
