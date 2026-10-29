"""
Base scraper interface.

Each job website has its own HTML structure, CSS classes, and field names.
A single generic selector (e.g. soup.find("h1")) fails on many sites because:
  - Some use <h1>, others <h2 class="offer-title"> or <div class="job-title">
  - Company name may live in meta tags, sidebar blocks, or JSON-LD
  - Main content may be loaded by JavaScript (needs Playwright later)

Every website scraper implements scrape(url) and returns RawJobPosting.
The LLM normalization step is intentionally NOT done here.
"""

from abc import ABC, abstractmethod

from models.raw_job import RawJobPosting


class BaseScraper(ABC):
    """Common contract for all website scrapers."""

    source_name: str

    @classmethod
    @abstractmethod
    def can_handle(cls, url: str) -> bool:
        """Return True if this scraper supports the given URL."""

    @abstractmethod
    def scrape(self, url: str) -> RawJobPosting:
        """
        Stage A only: fetch HTML and extract RawJobPosting.

        Raises on unrecoverable errors (HTTP failure, empty page, etc.).
        Missing optional fields should be None, not invented.
        """
