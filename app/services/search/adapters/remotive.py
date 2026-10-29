"""Remotive public remote-jobs API. No key. Attribution: keep the Remotive listing URL."""

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

SEARCH_URL = "https://remotive.com/api/remote-jobs"


class RemotiveSearchAdapter(BaseJobSearchAdapter):
    source_name = "remotive"
    display_name = "Remotive"
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

        payload = fetch_feed(f"{SEARCH_URL}?{urlencode({'search': query.strip(), 'limit': max(limit, 50)})}")
        rows = payload.get("jobs")
        if not isinstance(rows, list):
            return []

        jobs: list[DiscoveredJob] = []
        seen: set[str] = set()
        for item in rows:
            job = _from_item(item, query.strip(), location)
            if job is None or job.url in seen:
                continue
            seen.add(job.url)
            jobs.append(job)
            if len(jobs) >= limit:
                break
        logger.info("Remotive discovery completed jobs_found=%d", len(jobs))
        return jobs


def _from_item(item: object, query: str, location: str | None) -> DiscoveredJob | None:
    if not isinstance(item, dict):
        return None
    title = str(item.get("title") or "").strip()
    company = str(item.get("company_name") or "").strip()
    place = str(item.get("candidate_required_location") or "").strip()
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
        source="remotive",
        metadata={
            "structured": True,
            "extraction_path": "remotive_api",
            "skills": [str(tag) for tag in tags if str(tag).strip()],
            "contract_type": str(item.get("job_type") or "") or None,
            "salary": str(item.get("salary") or "") or None,
        },
    )
