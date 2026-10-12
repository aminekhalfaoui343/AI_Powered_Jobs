import pytest
import asyncio

from app.services.search.dedupe import deduplicate_discovered_jobs
from app.services.search.adapters.france_travail import FranceTravailSearchAdapter
from app.services.search.search_service import JobSearchService
from models.discovered_job import DiscoveredJob
from models.search_request import JobSearchRequest


def test_search_request_accepts_query_and_location():
    request = JobSearchRequest(
        query="Python Developer",
        location="France",
        sources=["france_travail"],
        max_results_per_source=10,
    )

    assert request.query == "Python Developer"
    assert request.location == "France"
    assert request.sources == ["france_travail"]
    assert request.max_results_per_source == 10


def test_france_travail_search_uses_public_page_without_oauth(monkeypatch):
    monkeypatch.delenv("FRANCE_TRAVAIL_CLIENT_ID", raising=False)
    monkeypatch.delenv("FRANCE_TRAVAIL_CLIENT_SECRET", raising=False)

    html = """
    <a href="/offres/recherche/detail/ABC123">
      <h2><span class="media-heading-title">Platform Engineer</span></h2>
      <p class="description">Long description should not become the title.</p>
    </a>
    <a href="/offres/recherche/detail/ABC123"><h2>Duplicate</h2></a>
    <a href="https://example.com/offres/recherche/detail/OTHER"><h2>External</h2></a>
    """
    requested = {}

    class FakeResponse:
        text = html

        @staticmethod
        def raise_for_status():
            return None

    def fake_get(url, headers, timeout):
        requested.update(url=url, headers=headers, timeout=timeout)
        return FakeResponse()

    def reject_oauth(*args, **kwargs):
        pytest.fail("France Travail public-page search must not request an OAuth token")

    monkeypatch.setattr("app.services.search.adapters.france_travail.requests.get", fake_get)
    monkeypatch.setattr("app.services.search.adapters.france_travail.requests.post", reject_oauth)

    jobs = FranceTravailSearchAdapter()._search_jobs("DevOps Engineer", "France", limit=10)

    assert len(jobs) == 1
    assert jobs[0].title == "Platform Engineer"
    assert jobs[0].location == "France"
    assert jobs[0].url == "https://candidat.francetravail.fr/offres/recherche/detail/ABC123"
    assert "motsCles=DevOps+Engineer" in requested["url"]
    assert "lieu=France" in requested["url"]
    assert requested["headers"]["User-Agent"] == "Mozilla/5.0"
    assert requested["timeout"] == (5, 30)


def test_deduplicate_discovered_jobs_removes_duplicate_urls():
    jobs = [
        DiscoveredJob(
            title="Python Developer",
            company="Acme",
            location="Paris",
            url="https://example.com/jobs/123?utm=1",
            source="france_travail",
        ),
        DiscoveredJob(
            title="Python Developer",
            company="Acme",
            location="Paris",
            url="https://example.com/jobs/123",
            source="france_travail",
        ),
        DiscoveredJob(
            title="DevOps Engineer",
            company="Beta",
            location="Lyon",
            url="https://example.com/jobs/456",
            source="france_travail",
        ),
    ]

    unique_jobs, skipped = deduplicate_discovered_jobs(jobs)

    assert len(unique_jobs) == 2
    assert skipped == 1
    assert unique_jobs[0].url == "https://example.com/jobs/123"
    assert unique_jobs[1].url == "https://example.com/jobs/456"


def test_deduplicate_discovered_jobs_merges_matching_metadata_across_sources():
    jobs = [
        DiscoveredJob(
            title="DevOps Engineer",
            company="Acme",
            location="Paris",
            url="https://france-travail.example/job/1",
            source="france_travail",
        ),
        DiscoveredJob(
            title=" DevOps  Engineer ",
            company="ACME",
            location="Paris",
            url="https://hellowork.example/job/2",
            source="hellowork",
        ),
    ]

    unique_jobs, skipped = deduplicate_discovered_jobs(jobs)

    assert len(unique_jobs) == 1
    assert skipped == 1
    assert unique_jobs[0].sources == ["france_travail", "hellowork"]


def test_job_search_request_rejects_blank_query():
    with pytest.raises(ValueError):
        JobSearchRequest(query="   ")


@pytest.mark.asyncio
async def test_search_runs_sources_in_parallel_and_isolates_failure(monkeypatch):
    service = JobSearchService()
    active = 0
    peak = 0

    class FakeAdapter:
        is_available = True

        def __init__(self, source_name: str, fails: bool = False):
            self.source_name = source_name
            self.fails = fails

        async def search_jobs(self, query, location=None, limit=20):
            nonlocal active, peak
            active += 1
            peak = max(peak, active)
            await asyncio.sleep(0.01)
            active -= 1
            if self.fails:
                raise RuntimeError("source failed")
            return [DiscoveredJob(url=f"https://{self.source_name}.example/job", source=self.source_name)]

    service.adapters = {
        "working": FakeAdapter("working"),
        "broken": FakeAdapter("broken", fails=True),
    }
    monkeypatch.setattr("app.services.search.search_service.list_enabled_sources", lambda: ["working", "broken"])

    result = await service.search(JobSearchRequest(query="DevOps", sources=["working", "broken"]))

    assert peak == 2
    assert len(result.jobs) == 1
    assert result.sources["working"] == {"status": "success", "jobs_found": 1}
    assert result.sources["broken"]["status"] == "failed"


@pytest.mark.asyncio
async def test_all_uses_only_enabled_sources(monkeypatch):
    service = JobSearchService()

    class FakeAdapter:
        is_available = True

        async def search_jobs(self, query, location=None, limit=20):
            return []

    service.adapters = {"enabled": FakeAdapter(), "disabled": FakeAdapter()}
    monkeypatch.setattr("app.services.search.search_service.list_enabled_sources", lambda: ["enabled"])

    result = await service.search(JobSearchRequest(query="Python", sources=["all"]))

    assert list(result.sources) == ["enabled"]
