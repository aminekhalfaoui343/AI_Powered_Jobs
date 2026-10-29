"""Jobicy public remote-jobs API. No key. Attribution: keep the Jobicy listing URL."""

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

SEARCH_URL = "https://jobicy.com/api/v2/remote-jobs"


class JobicySearchAdapter(BaseJobSearchAdapter):
    source_name = "jobicy"
    display_name = "Jobicy"
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

        params: dict[str, str | int] = {"count": min(max(limit, 20), 100), "geo": "europe"}
        tag = query.strip()
        if 3 <= len(tag) <= 50:
            params["tag"] = tag
        payload = fetch_feed(f"{SEARCH_URL}?{urlencode(params)}")
        rows = payload.get("jobs")
        if not isinstance(rows, list) or not rows:
            fallback = {"count": params["count"]}
            if "tag" in params:
                fallback["tag"] = params["tag"]
            payload = fetch_feed(f"{SEARCH_URL}?{urlencode(fallback)}")
            rows = payload.get("jobs") if isinstance(payload.get("jobs"), list) else []

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
        logger.info("Jobicy discovery completed jobs_found=%d", len(jobs))
        return jobs


def _from_item(item: object, query: str, location: str | None) -> DiscoveredJob | None:
    if not isinstance(item, dict):
        return None
    title = str(item.get("jobTitle") or item.get("title") or "").strip()
    company = str(item.get("companyName") or item.get("company") or "").strip()
    place = str(item.get("jobGeo") or item.get("geo") or "").strip()
    url = str(item.get("url") or "").strip()
    description = html_to_text(item.get("jobDescription") or item.get("jobExcerpt") or item.get("description"))
    tags = item.get("jobIndustry") if isinstance(item.get("jobIndustry"), list) else []
    if isinstance(item.get("jobTags"), list):
        tags = [*tags, *item["jobTags"]]
    if not title or not url:
        return None
    if not matches_query(query, title, company, description, place, " ".join(str(tag) for tag in tags)):
        return None
    if not matches_requested_location(location, place, title, description):
        return None
    return DiscoveredJob(
        title=title[:200],
        company=company or None,
        location=place or location or "France / Remote",
        description=description or None,
        url=url,
        source="jobicy",
        metadata={
            "structured": True,
            "extraction_path": "jobicy_api",
            "skills": [str(tag) for tag in tags if str(tag).strip()],
            "contract_type": str(item.get("jobType") or "") or None,
            "salary": str(item.get("jobSalary") or "") or None,
        },
    )
