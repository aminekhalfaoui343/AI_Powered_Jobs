from __future__ import annotations

from app.services.search.base import BaseJobSearchAdapter, SourceUnavailableError
from models.discovered_job import DiscoveredJob


class UnavailableSourceAdapter(BaseJobSearchAdapter):
    """Placeholder for a source pending an approved API/feed or page adapter."""

    is_available = False

    def __init__(self, source_name: str, display_name: str, access_type: str):
        self.source_name = source_name
        self.display_name = display_name
        self.access_type = access_type

    async def search_jobs(
        self,
        query: str,
        location: str | None = None,
        limit: int = 20,
    ) -> list[DiscoveredJob]:
        raise SourceUnavailableError("Source not currently supported")