"""Adapter for the existing Stage A scraper."""

from models.raw_job import RawJobPosting
from pipeline.run import scrape_job as existing_scrape_job


def scrape_job(url: str) -> RawJobPosting:
    """Connect the queue workflow to the project's existing scraper."""
    # Keep all website-specific scraping in scrapers/ and pipeline/run.py.
    return existing_scrape_job(url)