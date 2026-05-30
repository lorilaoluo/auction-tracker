"""CLI entry point for auction-tracker."""
import logging
import click

from auction_tracker.database import Database
from auction_tracker.models import ScrapeReport
from auction_tracker.scraper.holmwood import HolmwoodScraper
from auction_tracker.scraper.grenadier import GrenadierScraper

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

SCRAPERS = [HolmwoodScraper, GrenadierScraper]


@click.group()
def main():
    """Christchurch Auction Results Tracker."""


@main.command()
@click.option("--days", default=7, type=int, help="Only fetch results from the last N days. Use 0 for all.")
def scrape(days):
    """Scrape auction results from all agencies."""
    lookback = days if days > 0 else None
    db = Database()
    agency_results = {}
    errors = {}

    for scraper_cls in SCRAPERS:
        scraper = scraper_cls()
        try:
            results = scraper.scrape(lookback_days=lookback)
            count = 0
            for r in results:
                count += db.insert(r)
            agency_results[scraper.agency_name] = count
            logger.info(f"{scraper.agency_name}: {count} new results")
        except Exception as e:
            errors[scraper.agency_name] = str(e)
            logger.error(f"{scraper.agency_name}: FAILED — {e}")

    db.close()
    report = ScrapeReport(agency_results, errors)

    if errors:
        logger.info(f"\n{len(errors)} agency(s) failed: {', '.join(errors.keys())}")

    if report.all_failed:
        logger.error("All scrapers failed.")
        raise SystemExit(1)

    logger.info(f"Done. {report.total_new} new results total.")


@main.command()
def view():
    """Launch the Streamlit dashboard."""
    import subprocess
    import sys
    from pathlib import Path

    dashboard_path = Path(__file__).parent / "dashboard.py"
    subprocess.run([sys.executable, "-m", "streamlit", "run", str(dashboard_path)])


@main.command()
def stats():
    """Print a quick summary of the database."""
    db = Database()
    s = db.get_stats()
    click.echo(f"Total sales tracked: {s['total']}")
    click.echo(f"Sales with prices:  {s['with_price']}")
    if s["median_price"]:
        click.echo(f"Median sale price:  ${s['median_price']:,.0f}")
        click.echo(f"Average sale price: ${s['avg_price']:,.0f}")
        click.echo(f"Lowest sale:        ${s['min_price']:,.0f}")
        click.echo(f"Highest sale:       ${s['max_price']:,.0f}")

    last = db.get_last_scrape_per_agency()
    if last:
        click.echo("\nLast scrape per agency:")
        for agency, ts in last.items():
            click.echo(f"  {agency}: {ts}")

    db.close()


if __name__ == "__main__":
    main()
