import asyncio

import pytest

from app.services.search.adapters.hellowork import (
    HelloWorkAccessDeniedError,
    HelloWorkParseError,
    HelloWorkProviderError,
    HelloWorkProviderResponse,
    HelloWorkRateLimitedError,
    HelloWorkSearchAdapter,
)
from app.services.search.base import SourceUnavailableError
from app.services.search.registry import SOURCE_REGISTRY
from models.discovered_job import DiscoveredJob


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
    return asyncio.run(HelloWorkSearchAdapter(provider=provider).search_jobs("DevOps", "Paris", limit))


def test_403_is_access_denied_and_not_retried():
    provider = FakeProvider(HelloWorkProviderResponse(status_code=403))

    with pytest.raises(HelloWorkAccessDeniedError, match="HTTP 403"):
        run_search(provider)

    assert provider.starts == [0]


def test_429_is_rate_limited_and_not_retried():
    provider = FakeProvider(HelloWorkProviderResponse(status_code=429))

    with pytest.raises(HelloWorkRateLimitedError, match="HTTP 429"):
        run_search(provider)

    assert provider.starts == [0]


@pytest.mark.parametrize("error", [TimeoutError("timeout"), OSError("connection failed")])
def test_network_failures_are_classified(error):
    with pytest.raises(HelloWorkProviderError, match="HelloWork provider"):
        run_search(FakeProvider(error=error))


def test_empty_response_returns_no_jobs():
    provider = FakeProvider(HelloWorkProviderResponse(status_code=200, jobs=[]))

    assert run_search(provider) == []


def test_malformed_response_is_classified_as_parse_failure():
    provider = FakeProvider(HelloWorkProviderResponse(status_code=200, jobs=None))

    with pytest.raises(HelloWorkParseError):
        run_search(provider)


def test_approved_provider_response_discovers_and_deduplicates_jobs():
    provider = FakeProvider(
        HelloWorkProviderResponse(
            status_code=200,
            jobs=[
                DiscoveredJob(
                    title="DevOps Engineer",
                    company="Acme",
                    location="Paris",
                    url="https://www.hellowork.com/offre/abc123",
                    source="hellowork",
                ),
                DiscoveredJob(
                    title="Duplicate",
                    url="https://www.hellowork.com/offre/abc123",
                    source="hellowork",
                ),
                DiscoveredJob(
                    title="Cloud Engineer",
                    url="https://www.hellowork.com/offre/def456",
                    source="hellowork",
                ),
            ],
        )
    )

    jobs = run_search(provider, limit=2)

    assert [job.url for job in jobs] == [
        "https://www.hellowork.com/offre/abc123",
        "https://www.hellowork.com/offre/def456",
    ]
    assert jobs[0].company == "Acme"
    assert provider.starts == [0]


def test_default_adapter_is_safely_unavailable():
    adapter = HelloWorkSearchAdapter()

    assert adapter.is_available is False
    with pytest.raises(SourceUnavailableError, match="approved HelloWork API"):
        run_search(adapter._provider)


def test_hellowork_is_registered_but_not_available_by_default():
    assert isinstance(SOURCE_REGISTRY["hellowork"], HelloWorkSearchAdapter)
    assert SOURCE_REGISTRY["hellowork"].is_available is False
