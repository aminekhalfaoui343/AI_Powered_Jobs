"""
Students-Jobs.fr scraper — student / internship oriented listings.

Example URL pattern (verify on the live site):
  https://www.students-jobs.fr/offre/...

Playwright candidate: MAYBE if listings are loaded via JavaScript

If this scraper returns empty fields, inspect the detail page HTML manually
and adjust the selectors in _extract_* methods.
"""

import logging

from bs4 import BeautifulSoup

from models.raw_job import RawJobPosting
from scrapers.base import BaseScraper
from utils.http import fetch_html
from utils.text import build_raw_text, element_text, soup_from_html

logger = logging.getLogger(__name__)


class StudentsJobsScraper(BaseScraper):
    source_name = "Students-Jobs.fr"

    @classmethod
    def can_handle(cls, url: str) -> bool:
        return "students-jobs.fr" in url.lower()

    def scrape(self, url: str) -> RawJobPosting:
        html = fetch_html(url)
        soup = soup_from_html(html)

        if len(html.strip()) < 300:
            raise ValueError("Page content too short — possible block or empty response")

        title = self._first_text(
            soup,
            "h1",
            ".offer-title",
            ".job-title",
            "meta[property='og:title']",
        )
        company = self._first_text(
            soup,
            ".company",
            ".company-name",
            "[class*='company']",
            "[class*='employeur']",
        )
        location = self._first_text(
            soup,
            ".location",
            ".city",
            "[class*='location']",
            "[class*='lieu']",
        )

        raw_text = build_raw_text(
            soup,
            main_selector=".offer-content, .job-content, .description, article, main",
        )
        if len(raw_text) < 80:
            raw_text = build_raw_text(soup)

        if not raw_text:
            raise ValueError(
                "Could not extract job text from Students-Jobs.fr. "
                "The page may be JavaScript-rendered — candidate for Playwright."
            )

        logger.info(
            "Students-Jobs scrape complete — title=%r company=%r location=%r",
            title,
            company,
            location,
        )

        return RawJobPosting(
            url=url,
            title=title,
            company=company,
            location=location,
            raw_text=raw_text,
            source=self.source_name,
        )

    def _first_text(self, soup: BeautifulSoup, *selectors: str) -> str | None:
        for selector in selectors:
            if selector.startswith("meta"):
                tag = soup.select_one(selector)
                if tag and tag.get("content"):
                    return tag["content"].strip()
            else:
                text = element_text(soup.select_one(selector))
                if text:
                    return text
        return None
