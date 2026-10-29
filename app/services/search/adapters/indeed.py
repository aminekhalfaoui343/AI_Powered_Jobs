"""Indeed discovery integration boundary.

Indeed's public site is not a permitted scraping interface for this
application. An approved provider must return normalized jobs through the
provider contract below; this adapter never fetches or parses Indeed HTML.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Protocol

from app.services.search.base import BaseJobSearchAdapter, SourceUnavailableError
from models.discovered_job import DiscoveredJob

logger = logging.getLogger(__name__)


class IndeedAccessDeniedError(SourceUnavailableError):
    """The provider denied access and must not be retried automatically."""


class IndeedRateLimitedError(SourceUnavailableError):
    """The provider is rate limiting requests."""


class IndeedProviderError(RuntimeError):
    """The configured provider failed due to a network or service error."""


class IndeedParseError(RuntimeError):
    """The approved provider returned an unexpected response shape."""


@dataclass(frozen=True)
class IndeedProviderResponse:
    status_code: int
    jobs: list[DiscoveredJob] | None = None


class IndeedProvider(Protocol):
    """Contract for an approved Indeed API or partner integration."""

    async def search(
        self, query: str, location: str | None, start: int
    ) -> IndeedProviderResponse:
        """Return normalized jobs without exposing credentials to callers."""


class UnavailableIndeedProvider:
    async def search(
        self, query: str, location: str | None, start: int
    ) -> IndeedProviderResponse:
        raise SourceUnavailableError(
            "Indeed discovery is unavailable: configure an approved Indeed API or partner provider. "
            "The public Indeed site cannot be scraped by this application."
        )


class IndeedSearchAdapter(BaseJobSearchAdapter):
    """Discover Indeed jobs only through an explicitly approved provider."""

    source_name = "indeed"
    display_name = "Indeed"
    access_type = "approved_api_or_partner_required"
    _max_pages = 3

    def __init__(self, provider: IndeedProvider | None = None):
        self._provider = provider or UnavailableIndeedProvider()
        self.is_available = provider is not None

    async def search_jobs(
        self, query: str, location: str | None = None, limit: int = 20
    ) -> list[DiscoveredJob]:
        if not query or not query.strip():
            raise ValueError("Search query cannot be blank")
        if limit <= 0:
            return []

        logger.info("Indeed discovery started source=%s operation=search", self.source_name)
        jobs: list[DiscoveredJob] = []
        seen_urls: set[str] = set()

        for page in range(self._max_pages):
            try:
                response = await self._provider.search(query.strip(), location, page * 10)
            except SourceUnavailableError:
                logger.warning("Indeed discovery unavailable source=%s operation=search", self.source_name)
                raise
            except TimeoutError as exc:
                logger.warning("Indeed discovery timeout source=%s operation=search", self.source_name)
                raise IndeedProviderError("Indeed provider timed out during discovery") from exc
            except OSError as exc:
                logger.warning("Indeed discovery network failure source=%s operation=search", self.source_name)
                raise IndeedProviderError("Indeed provider network failure during discovery") from exc

            self._raise_for_status(response.status_code)
            if response.jobs is None:
                logger.warning(
                    "Indeed discovery response parsing failed source=%s operation=parse status=%d",
                    self.source_name,
                    response.status_code,
                )
                raise IndeedParseError("Indeed provider returned no normalized job payload")
            if not response.jobs:
                logger.info(
                    "Indeed discovery returned no jobs source=%s operation=search status=%d",
                    self.source_name,
                    response.status_code,
                )
                break

            for job in response.jobs:
                if job.url in seen_urls:
                    continue
                jobs.append(job)
                seen_urls.add(job.url)
                if len(jobs) >= limit:
                    return jobs

        logger.info(
            "Indeed discovery completed source=%s operation=search jobs_found=%d",
            self.source_name,
            len(jobs),
        )
        return jobs

    @staticmethod
    def _raise_for_status(status_code: int) -> None:
        if status_code == 403:
            raise IndeedAccessDeniedError(
                "Indeed denied access (HTTP 403). Configure an approved Indeed API or partner provider; "
                "do not retry the public site."
            )
        if status_code == 429:
            raise IndeedRateLimitedError(
                "Indeed rate limited the provider (HTTP 429). Retry only according to the approved provider's policy."
            )
        if status_code >= 400:
            raise IndeedProviderError(f"Indeed provider returned HTTP {status_code}")
