"""HelloWork discovery integration boundary.

HelloWork public job pages are not a permitted scraping interface for this
application. An approved provider, API, or partner integration must return
normalized jobs through the provider contract below.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Protocol

from app.services.search.base import BaseJobSearchAdapter, SourceUnavailableError
from models.discovered_job import DiscoveredJob

logger = logging.getLogger(__name__)


class HelloWorkAccessDeniedError(SourceUnavailableError):
    """The provider denied access and must not be retried automatically."""


class HelloWorkRateLimitedError(SourceUnavailableError):
    """The provider is rate limiting requests."""


class HelloWorkProviderError(RuntimeError):
    """The configured provider failed due to a network or service error."""


class HelloWorkParseError(RuntimeError):
    """The approved provider returned an unexpected response shape."""


@dataclass(frozen=True)
class HelloWorkProviderResponse:
    status_code: int
    jobs: list[DiscoveredJob] | None = None


class HelloWorkProvider(Protocol):
    """Contract for an approved HelloWork API or partner integration."""

    async def search(
        self, query: str, location: str | None, start: int
    ) -> HelloWorkProviderResponse:
        """Return normalized jobs without exposing credentials to callers."""


class UnavailableHelloWorkProvider:
    async def search(
        self, query: str, location: str | None, start: int
    ) -> HelloWorkProviderResponse:
        raise SourceUnavailableError(
            "HelloWork discovery is unavailable: configure an approved HelloWork API or partner provider. "
            "The public HelloWork site cannot be scraped by this application."
        )


class HelloWorkSearchAdapter(BaseJobSearchAdapter):
    """Discover HelloWork jobs only through an explicitly approved provider."""

    source_name = "hellowork"
    display_name = "HelloWork"
    access_type = "approved_api_or_partner_required"
    _max_pages = 3

    def __init__(self, provider: HelloWorkProvider | None = None):
        self._provider = provider or UnavailableHelloWorkProvider()
        self.is_available = provider is not None

    async def search_jobs(
        self, query: str, location: str | None = None, limit: int = 20
    ) -> list[DiscoveredJob]:
        if not query or not query.strip():
            raise ValueError("Search query cannot be blank")
        if limit <= 0:
            return []

        logger.info("HelloWork discovery started source=%s operation=search", self.source_name)
        jobs: list[DiscoveredJob] = []
        seen_urls: set[str] = set()

        for page in range(self._max_pages):
            try:
                response = await self._provider.search(query.strip(), location, page * 10)
            except SourceUnavailableError:
                logger.warning("HelloWork discovery unavailable source=%s operation=search", self.source_name)
                raise
            except TimeoutError as exc:
                logger.warning("HelloWork discovery timeout source=%s operation=search", self.source_name)
                raise HelloWorkProviderError("HelloWork provider timed out during discovery") from exc
            except OSError as exc:
                logger.warning("HelloWork discovery network failure source=%s operation=search", self.source_name)
                raise HelloWorkProviderError("HelloWork provider network failure during discovery") from exc

            self._raise_for_status(response.status_code)
            if response.jobs is None:
                logger.warning(
                    "HelloWork discovery response parsing failed source=%s operation=parse status=%d",
                    self.source_name,
                    response.status_code,
                )
                raise HelloWorkParseError("HelloWork provider returned no normalized job payload")
            if not response.jobs:
                logger.info(
                    "HelloWork discovery returned no jobs source=%s operation=search status=%d",
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
            "HelloWork discovery completed source=%s operation=search jobs_found=%d",
            self.source_name,
            len(jobs),
        )
        return jobs

    @staticmethod
    def _raise_for_status(status_code: int) -> None:
        if status_code == 403:
            raise HelloWorkAccessDeniedError(
                "HelloWork denied access (HTTP 403). Configure an approved HelloWork API or partner provider; "
                "do not retry the public site."
            )
        if status_code == 429:
            raise HelloWorkRateLimitedError(
                "HelloWork rate limited the provider (HTTP 429). Retry only according to the approved provider's policy."
            )
        if status_code >= 400:
            raise HelloWorkProviderError(f"HelloWork provider returned HTTP {status_code}")
