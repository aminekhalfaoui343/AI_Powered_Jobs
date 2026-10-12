import asyncio

import pytest

from app.services.search.adapters.indeed import (
    IndeedAccessDeniedError,
    IndeedParseError,
    IndeedProviderError,
    IndeedProviderResponse,
    IndeedRateLimitedError,
    IndeedSearchAdapter,
)
from app.services.search.base import SourceUnavailableError
from app.services.search.registry import SOURCE_REGISTRY
from app.services.search.search_service import JobSearchService
from models.discovered_job import DiscoveredJob
from models.search_request import JobSearchRequest
from scrapers.indeed import IndeedScraper


class FakeProvider:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.starts = []

    async def search(self, query, location, start):
        self.starts.append(start)
        if self.error:
            raise self.error
        return self.response


def run_search(provider, limit=3):
    return asyncio.run(IndeedSearchAdapter(provider=provider).search_jobs("Python", "Paris", limit))


def test_403_is_access_denied_and_not_retried():
    provider = FakeProvider(IndeedProviderResponse(status_code=403))

    with pytest.raises(IndeedAccessDeniedError, match="HTTP 403"):
        run_search(provider)

    assert provider.starts == [0]


def test_429_is_rate_limited_and_not_retried():
    provider = FakeProvider(IndeedProviderResponse(status_code=429))

    with pytest.raises(IndeedRateLimitedError, match="HTTP 429"):
        run_search(provider)

    assert provider.starts == [0]


@pytest.mark.parametrize("error", [TimeoutError("timeout"), OSError("connection failed")])
def test_network_failures_are_classified(error):
    with pytest.raises(IndeedProviderError, match="Indeed provider"):
        run_search(FakeProvider(error=error))


def test_empty_response_returns_no_jobs():
    provider = FakeProvider(IndeedProviderResponse(status_code=200, jobs=[]))

    assert run_search(provider) == []


def test_malformed_response_is_classified_as_parse_failure():
    provider = FakeProvider(IndeedProviderResponse(status_code=200, jobs=None))

    with pytest.raises(IndeedParseError):
        run_search(provider)


def test_approved_provider_response_discovers_and_deduplicates_jobs():
    provider = FakeProvider(
        IndeedProviderResponse(
            status_code=200,
            jobs=[
                DiscoveredJob(
                    title="Python Developer",
                    company="Acme",
                    location="Paris",
                    url="https://fr.indeed.com/viewjob?jk=abc123",
                    source="indeed",
                ),
                DiscoveredJob(
                    title="Duplicate",
                    url="https://fr.indeed.com/viewjob?jk=abc123",
                    source="indeed",
                ),
                DiscoveredJob(
                    title="Backend Engineer",
                    url="https://fr.indeed.com/viewjob?jk=def456",
                    source="indeed",
                ),
            ],
        )
    )

    jobs = run_search(provider, limit=2)

    assert [job.url for job in jobs] == [
        "https://fr.indeed.com/viewjob?jk=abc123",
        "https://fr.indeed.com/viewjob?jk=def456",
    ]
    assert jobs[0].company == "Acme"
    assert provider.starts == [0]


def test_default_adapter_is_safely_unavailable():
    adapter = IndeedSearchAdapter()

    assert adapter.is_available is False
    with pytest.raises(SourceUnavailableError, match="approved Indeed API"):
        run_search(adapter._provider)


def test_indeed_is_registered_but_not_available_by_default():
    assert isinstance(SOURCE_REGISTRY["indeed"], IndeedSearchAdapter)
    assert SOURCE_REGISTRY["indeed"].is_available is False


def test_detail_scraper_does_not_fetch_public_indeed_pages():
    with pytest.raises(SourceUnavailableError, match="cannot be scraped"):
        IndeedScraper().scrape("https://fr.indeed.com/viewjob?jk=abc123")


@pytest.mark.asyncio
async def test_indeed_failure_does_not_prevent_other_sources(monkeypatch):
    class WorkingAdapter:
        is_available = True

        async def search_jobs(self, query, location=None, limit=20):
            return [DiscoveredJob(url="https://other.example/job/1", source="other")]

    service = JobSearchService()
    service.adapters = {"indeed": IndeedSearchAdapter(), "other": WorkingAdapter()}
    monkeypatch.setattr(
        "app.services.search.search_service.list_enabled_sources",
        lambda: ["indeed", "other"],
    )

    result = await service.search(JobSearchRequest(query="Python", sources=["indeed", "other"]))

    assert len(result.jobs) == 1
    assert result.jobs[0].source == "other"
    assert result.sources["indeed"]["status"] == "unavailable"
    assert result.sources["other"] == {"status": "success", "jobs_found": 1}
