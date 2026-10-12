"""Indeed detail integration guard.

Indeed public job pages are not a permitted automated scraping interface for
this application. A future approved provider should return normalized data
directly or add a separate, contract-approved detail implementation.
"""

from app.services.search.base import SourceUnavailableError
from models.raw_job import RawJobPosting
from scrapers.base import BaseScraper


class IndeedScraper(BaseScraper):
    source_name = "Indeed"

    @classmethod
    def can_handle(cls, url: str) -> bool:
        return "indeed.com" in url.lower()

    def scrape(self, url: str) -> RawJobPosting:
        raise SourceUnavailableError(
            "Indeed detail scraping is unavailable: the public Indeed site cannot be scraped by this application. "
            "Use an approved Indeed API or partner provider."
        )
