from __future__ import annotations

import asyncio
import logging
from urllib.parse import urlencode, urljoin, urlsplit

import requests
from bs4 import BeautifulSoup

from app.services.search.base import BaseJobSearchAdapter
from models.discovered_job import DiscoveredJob

logger = logging.getLogger(__name__)


class FranceTravailSearchAdapter(BaseJobSearchAdapter):
    """Discover listings from France Travail's public search page."""

    source_name = "france_travail"
    display_name = "France Travail"
    access_type = "public_page"
    search_url = "https://candidat.francetravail.fr/offres/recherche"

    async def search_jobs(
        self, query: str, location: str | None = None, limit: int = 20
    ) -> list[DiscoveredJob]:
        return await asyncio.to_thread(self._search_jobs, query, location, limit)

    def _search_jobs(
        self, query: str, location: str | None = None, limit: int = 20
    ) -> list[DiscoveredJob]:
        if not query or not query.strip():
            raise ValueError("Search query cannot be blank")
        if limit <= 0:
            return []

        params = {"motsCles": query.strip()}
        if location and location.strip():
            params["lieu"] = location.strip()

        page_url = f"{self.search_url}?{urlencode(params)}"
        logger.info("Searching France Travail public page: %s", page_url)
        try:
            response = requests.get(
                page_url,
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=(5, 30),
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise RuntimeError(f"France Travail public search failed: {exc}") from exc

        soup = BeautifulSoup(response.text or "", "html.parser")
        jobs: list[DiscoveredJob] = []
        seen_urls: set[str] = set()
        for anchor in soup.select("a[href]"):
            url = self._normalize_job_url(anchor.get("href", ""))
            if not url or url in seen_urls or not self._looks_like_detail_url(url):
                continue

            title_element = anchor.select_one(".media-heading-title, h2")
            title = (
                title_element.get_text(" ", strip=True)
                if title_element
                else anchor.get_text(" ", strip=True)
            ) or query.strip()
            jobs.append(
                DiscoveredJob(
                    title=title[:200],
                    location=location,
                    url=url,
                    source=self.source_name,
                )
            )
            seen_urls.add(url)
            if len(jobs) >= limit:
                break

        return jobs

    @staticmethod
    def _normalize_job_url(href: str) -> str | None:
        if not href:
            return None
        url = href.strip()
        if url.startswith(("javascript:", "mailto:")):
            return None
        if url.startswith("/"):
            url = urljoin("https://candidat.francetravail.fr", url)
        parsed = urlsplit(url)
        if parsed.scheme not in {"http", "https"} or parsed.netloc != "candidat.francetravail.fr":
            return None
        return url

    @staticmethod
    def _looks_like_detail_url(url: str) -> bool:
        return "/offres/recherche/detail/" in url.lower()