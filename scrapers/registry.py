"""
Scraper registry — pick the right scraper from a job URL.

To add a new website later:
  1. Create scrapers/my_site.py implementing BaseScraper
  2. Import it here and append to SCRAPERS
    3. No changes needed in main.py or the LLM extractor
"""

import logging
from urllib.parse import urlparse

from scrapers.base import BaseScraper
from scrapers.france_travail import FranceTravailScraper
from scrapers.indeed import IndeedScraper
from scrapers.ouest_france_emploi import OuestFranceEmploiScraper
from scrapers.students_jobs import StudentsJobsScraper

logger = logging.getLogger(__name__)

# Order matters: first matching scraper wins.
SCRAPERS: list[type[BaseScraper]] = [
    FranceTravailScraper,
    IndeedScraper,
    OuestFranceEmploiScraper,
    StudentsJobsScraper,
]


def get_scraper_for_url(url: str) -> BaseScraper:
    """
    Identify the website from the URL domain and return its scraper instance.

    Raises:
        ValueError: no scraper registered for this domain
    """
    parsed = urlparse(url)
    domain = parsed.netloc.lower().removeprefix("www.")

    for scraper_cls in SCRAPERS:
        if scraper_cls.can_handle(url):
            logger.info("Selected scraper %s for domain %s", scraper_cls.__name__, domain)
            return scraper_cls()

    supported = ", ".join(sorted({s.source_name for s in SCRAPERS}))
    raise ValueError(
        f"No scraper registered for '{domain}'. "
        f"Currently supported sources: {supported}. "
        f"Add a new scraper in scrapers/ and register it in scrapers/registry.py."
    )


def list_supported_sources() -> list[str]:
    return [scraper.source_name for scraper in SCRAPERS]
