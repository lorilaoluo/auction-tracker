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
