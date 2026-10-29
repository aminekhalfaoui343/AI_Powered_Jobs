from __future__ import annotations

import logging
import asyncio
from dataclasses import dataclass

from app.services.search.base import BaseJobSearchAdapter, SourceUnavailableError
from models.discovered_job import DiscoveredJob
from models.search_request import JobSearchRequest
from app.services.search.registry import SOURCE_REGISTRY, list_enabled_sources

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    jobs: list[DiscoveredJob]
    sources: dict[str, dict[str, object]]


class JobSearchService:
    """Coordinates a request across the search adapters and normalizes the discovered jobs."""

    def __init__(self):
        self.adapters: dict[str, BaseJobSearchAdapter] = SOURCE_REGISTRY

    def list_supported_sources(self) -> list[str]:
        return sorted(self.adapters)

    def get_adapter(self, source: str | None) -> BaseJobSearchAdapter:
        if not source:
            source = "france_travail"
        adapter = self.adapters.get(source.lower())
        if adapter is None:
            raise ValueError(f"Unsupported source: {source}. Supported sources: {', '.join(self.list_supported_sources())}")
        return adapter

    async def search(self, payload: JobSearchRequest) -> SearchResult:
        requested_sources = payload.sources or ["france_travail"]
        if not requested_sources:
            requested_sources = ["france_travail"]

        if "all" in requested_sources:
            requested_sources = list_enabled_sources()

        normalized_sources = list(dict.fromkeys(source.lower() for source in requested_sources))
        known_sources = [source for source in normalized_sources if source in self.adapters]
        unknown_sources = [source for source in normalized_sources if source not in self.adapters]

        results = await asyncio.gather(
            *(self._search_source(source, payload) for source in known_sources)
        )
        discovered_jobs = [job for result in results for job in result[0]]
        source_results = {source: result[1] for source, result in zip(known_sources, results)}
        for source in unknown_sources:
            source_results[source] = {
                "status": "unavailable",
                "jobs_found": 0,
                "error": f"Unsupported source: {source}. Supported sources: {', '.join(self.list_supported_sources())}",
            }
        return SearchResult(jobs=discovered_jobs, sources=source_results)

    async def _search_source(
        self, source: str, payload: JobSearchRequest
    ) -> tuple[list[DiscoveredJob], dict[str, object]]:
        adapter = self.get_adapter(source)
        if source not in list_enabled_sources():
            return [], {"status": "disabled", "jobs_found": 0, "error": "Source disabled by configuration"}
        if not adapter.is_available:
            return [], {"status": "unavailable", "jobs_found": 0, "error": "Source not currently supported"}

        try:
            jobs = await adapter.search_jobs(
                query=payload.query,
                location=payload.location,
                limit=payload.max_results_per_source,
            )
        except SourceUnavailableError as exc:
            logger.warning("Search source %s unavailable: %s", source, exc)
            return [], {"status": "unavailable", "jobs_found": 0, "error": str(exc)}
        except Exception as exc:
            logger.exception("Search source %s failed", source)
            return [], {"status": "failed", "jobs_found": 0, "error": str(exc)}

        return jobs, {"status": "success", "jobs_found": len(jobs)}
