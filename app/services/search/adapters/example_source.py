from __future__ import annotations

import logging
import re
import asyncio
from urllib.parse import parse_qsl, quote_plus, urlencode, urljoin, urlsplit

import requests
from bs4 import BeautifulSoup

from app.services.search.base import BaseJobSearchAdapter
from models.discovered_job import DiscoveredJob

logger = logging.getLogger(__name__)


class FranceTravailSearchAdapter(BaseJobSearchAdapter):
    """Minimal search adapter for the France Travail jobs search page.

    This layer is intentionally discovery-only: it finds candidate job result URLs from a
    search page and normalizes them. The actual scrape/AI extraction still happens in the
    existing ARQ pipeline.
    """

    source_name = "france_travail"
    display_name = "France Travail"
    access_type = "public_api_or_page"

    async def search_jobs(self, query: str, location: str | None = None, limit: int = 20) -> list[DiscoveredJob]:
        return await asyncio.to_thread(self._search_jobs, query, location, limit)

    def _search_jobs(self, query: str, location: str | None = None, limit: int = 20) -> list[DiscoveredJob]:
        if not query or not query.strip():
            raise ValueError("Search query cannot be blank")

        search_query = query.strip()
        if location and location.strip():
            search_query = f"{search_query} {location.strip()}"

        params = {"motsCles": query.strip()}
        if location and location.strip():
            params["lieu"] = location.strip()

        page_url = "https://candidat.francetravail.fr/offres/recherche?" + urlencode(params)
        logger.info("Searching France Travail for %s via %s", search_query, page_url)

        try:
            response = requests.get(page_url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
            response.raise_for_status()
        except requests.RequestException as exc:
            raise RuntimeError(f"Search page request failed for {self.source_name}: {exc}") from exc

        html = response.text or ""
        if not html.strip():
            return []

        soup = BeautifulSoup(html, "html.parser")
        seen_urls: set[str] = set()
        jobs: list[DiscoveredJob] = []

        for candidate in soup.select("a[href]"):
            href = candidate.get("href") or ""
            if not href:
                continue
            normalized = self._normalize_job_url(href)
            if not normalized or normalized in seen_urls:
                continue
            if not self._looks_like_detail_url(normalized):
                continue

            title = (candidate.get_text(" ", strip=True) or query.strip())[:200]
            jobs.append(
                DiscoveredJob(
                    title=title,
                    company=None,
                    location=location,
                    url=normalized,
                    source=self.source_name,
                )
            )
            seen_urls.add(normalized)

            if len(jobs) >= limit:
                break

        return jobs

    @staticmethod
    def _normalize_job_url(href: str) -> str | None:
        if not href:
            return None
        url = href.strip()
        if url.startswith("javascript:") or url.startswith("mailto:"):
            return None
        if url.startswith("/"):
            url = urljoin("https://candidat.francetravail.fr", url)
        parsed = urlsplit(url)
        if not parsed.scheme or not parsed.netloc:
            return None
        return url

    @staticmethod
    def _looks_like_detail_url(url: str) -> bool:
        lower = url.lower()
        return "/recherche/detail/" in lower or "/offres/" in lower and "detail" in lower
