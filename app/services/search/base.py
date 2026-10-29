from __future__ import annotations

from abc import ABC, abstractmethod

from models.discovered_job import DiscoveredJob


class SourceUnavailableError(RuntimeError):
    """Raised when a source is known but cannot be queried safely."""


class BaseJobSearchAdapter(ABC):
    """Base contract for sources that discover multiple job URLs from a query."""

    source_name: str = ""
    display_name: str = ""
    access_type: str = "public_page"
    is_available: bool = True

    @classmethod
    def supports(cls, source_name: str) -> bool:
        return cls.source_name.lower() == source_name.lower()

    @abstractmethod
    async def search_jobs(
        self,
        query: str,
        location: str | None = None,
        limit: int = 20,
    ) -> list[DiscoveredJob]:
        """Return normalized job discovery results for one source."""
