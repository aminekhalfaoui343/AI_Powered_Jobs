"""
Pipeline orchestration — keeps Stage A (scraping) and Stage B (AI) separate.
"""

import logging

from extraction.openrouter_extractor import extract_job_posting, extract_job_posting_with_retry
from models.job_posting import JobPosting
from models.raw_job import RawJobPosting
from scrapers.registry import get_scraper_for_url

logger = logging.getLogger(__name__)


def scrape_job(url: str) -> RawJobPosting:
    """
    Stage A only: URL → website-specific scraper → RawJobPosting.
    """
    scraper = get_scraper_for_url(url)
    logger.info("Stage A — scraping with %s", scraper.__class__.__name__)
    return scraper.scrape(url)


async def extract_job(raw_job: RawJobPosting) -> JobPosting:
    """
    Stage B only: RawJobPosting -> OpenRouter -> JobPosting.
    """
    logger.info("Stage B - extracting structured data with OpenRouter")
    return await extract_job_posting_with_retry(raw_job)


async def run_pipeline(url: str) -> tuple[RawJobPosting, JobPosting]:
    """
    Full pipeline: scrape then extract.

    Returns both RawJobPosting and JobPosting so callers can inspect
    intermediate results for learning/debugging.
    """
    raw_job = scrape_job(url)
    job = await extract_job(raw_job)
    return raw_job, job
