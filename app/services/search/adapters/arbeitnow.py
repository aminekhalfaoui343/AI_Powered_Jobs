"""Arbeitnow public job-board API. No key. Filter client-side for France-relevant jobs."""

from __future__ import annotations

import asyncio
import logging
from urllib.parse import urlencode

from app.services.search.base import BaseJobSearchAdapter
from app.services.search.feeds import (
    fetch_feed,
    html_to_text,
    matches_query,
    matches_requested_location,
)
from models.discovered_job import DiscoveredJob

logger = logging.getLogger(__name__)

SEARCH_URL = "https://www.arbeitnow.com/api/job-board-api"
_MAX_PAGES = 3


class ArbeitnowSearchAdapter(BaseJobSearchAdapter):
    source_name = "arbeitnow"
    display_name = "Arbeitnow"
    access_type = "public_api"

    async def search_jobs(
        self, query: str, location: str | None = None, limit: int = 20
    ) -> list[DiscoveredJob]:
        return await asyncio.to_thread(self._search_jobs, query, location, limit)

    def _search_jobs(self, query: str, location: str | None, limit: int) -> list[DiscoveredJob]:
        if not query or not query.strip():
            raise ValueError("Search query cannot be blank")
        if limit <= 0:
            return []

        jobs: list[DiscoveredJob] = []
        seen: set[str] = set()
        for page in range(1, _MAX_PAGES + 1):
            payload = fetch_feed(f"{SEARCH_URL}?{urlencode({'page': page})}")
            rows = payload.get("data")
            if not isinstance(rows, list) or not rows:
                break
            for item in rows:
                job = _from_item(item, query.strip(), location)
                if job is None or job.url in seen:
                    continue
                seen.add(job.url)
                jobs.append(job)
                if len(jobs) >= limit:
                    return jobs
            links = payload.get("links") if isinstance(payload.get("links"), dict) else {}
            if not links.get("next"):
                break
        logger.info("Arbeitnow discovery completed jobs_found=%d", len(jobs))
        return jobs


def _from_item(item: object, query: str, location: str | None) -> DiscoveredJob | None:
    if not isinstance(item, dict):
        return None
    title = str(item.get("title") or "").strip()
    company = str(item.get("company_name") or "").strip()
    place = str(item.get("location") or "").strip()
    url = str(item.get("url") or "").strip()
    description = html_to_text(item.get("description"))
    tags = item.get("tags") if isinstance(item.get("tags"), list) else []
    if not title or not url:
        return None
    if not matches_query(query, title, company, description, " ".join(str(tag) for tag in tags)):
        return None
    if not matches_requested_location(location, place, title, description):
        return None
    return DiscoveredJob(
        title=title[:200],
        company=company or None,
        location=place or location or "France / Remote",
        description=description or None,
        url=url,
        source="arbeitnow",
        metadata={
            "structured": True,
            "extraction_path": "arbeitnow_api",
            "skills": [str(tag) for tag in tags if str(tag).strip()],
            "contract_type": ", ".join(str(value) for value in item.get("job_types") or [] if value),
            "remote": bool(item.get("remote")),
        },
    )
