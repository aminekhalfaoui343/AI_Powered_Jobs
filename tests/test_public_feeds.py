import pytest
import requests

from app.services.search.adapters.arbeitnow import _from_item as arbeitnow_from_item
from app.services.search.adapters.jobicy import _from_item as jobicy_from_item
from app.services.search.adapters.la_bonne_alternance import (
    LaBonneAlternanceSearchAdapter,
    _from_item as lba_from_item,
)
from app.services.search.adapters.remotive import _from_item as remotive_from_item
from app.services.search.base import SourceUnavailableError
from app.services.search.feeds import fetch_feed, matches_query, matches_requested_location
from app.services.search.registry import SOURCE_REGISTRY
from app.tasks import extraction_tasks
from models.raw_job import RawJobPosting


def test_france_market_filter_keeps_paris_and_rejects_unrelated():
    assert matches_requested_location("France", "Paris, France")
    assert matches_requested_location(None, "Remote - Europe")
    assert not matches_requested_location("France", "Austin, Texas, USA")
    assert not matches_requested_location(
        "France",
        "Berlin, Berlin, Germany",
        "AI / Machine Learning Engineer II",
        "Remote-friendly team with offices in Europe",
    )
    assert not matches_requested_location("France", "Germany (Remote)", "Solutions Architect", "")
    assert matches_requested_location("France", "Worldwide", "Python Developer", "")
    assert matches_requested_location("France", "Europe, USA, Canada, APAC", "Backend Engineer", "")


def test_query_tokens_match_title():
    assert matches_query("Python developer", "Senior Python Engineer", "Acme")
    assert not matches_query("Kubernetes", "Marketing intern", "Paris")


def test_arbeitnow_maps_structured_job():
    job = arbeitnow_from_item(
        {
            "title": "Python Developer",
            "company_name": "Acme",
            "location": "Paris, France",
            "url": "https://www.arbeitnow.com/jobs/python-developer",
            "description": "<p>Build APIs in Python.</p>",
            "tags": ["Python", "Django"],
            "job_types": ["full-time"],
            "remote": True,
        },
        "Python",
        "France",
    )
    assert job is not None
    assert job.source == "arbeitnow"
    assert job.company == "Acme"
    assert "Python" in job.metadata["skills"]
    assert "Build APIs" in (job.description or "")


def test_remotive_keeps_listing_url_for_attribution():
    job = remotive_from_item(
        {
            "title": "Backend Engineer",
            "company_name": "RemoteCo",
            "candidate_required_location": "France",
            "url": "https://remotive.com/remote-jobs/software-dev/backend-engineer-123",
            "description": "Django and PostgreSQL.",
            "tags": ["python"],
            "job_type": "full_time",
            "salary": "",
        },
        "Backend",
        None,
    )
    assert job is not None
    assert job.url.startswith("https://remotive.com/")


def test_jobicy_maps_job_title_fields():
    job = jobicy_from_item(
        {
            "jobTitle": "DevOps Engineer | France | Remote",
            "companyName": "Grafana Labs",
            "jobGeo": "France",
            "url": "https://jobicy.com/jobs/1-devops-engineer",
            "jobDescription": "Kubernetes and Terraform.",
            "jobTags": ["DevOps"],
            "jobType": "full-time",
        },
        "DevOps",
        "France",
    )
    assert job is not None
    assert job.source == "jobicy"
    assert job.title.startswith("DevOps")


def test_restricted_sources_are_registered_but_unavailable():
    assert SOURCE_REGISTRY["indeed"].is_available is False
    assert SOURCE_REGISTRY["hellowork"].is_available is False
    assert SOURCE_REGISTRY["welcome_to_the_jungle"].is_available is False
    assert SOURCE_REGISTRY["jobteaser"].is_available is False
    assert SOURCE_REGISTRY["apec"].is_available is False
    assert SOURCE_REGISTRY["arbeitnow"].is_available is True
    assert SOURCE_REGISTRY["remotive"].is_available is True
    assert SOURCE_REGISTRY["jobicy"].is_available is True
    assert SOURCE_REGISTRY["la_bonne_alternance"].source_name == "la_bonne_alternance"
    assert "linkedin" not in SOURCE_REGISTRY


def test_fetch_feed_maps_rate_limit_to_unavailable(monkeypatch):
    class FakeResponse:
        status_code = 429

        def raise_for_status(self):
            raise AssertionError("429 must be mapped before raise_for_status")

        def json(self):
            return {}

    monkeypatch.setattr("app.services.search.feeds.requests.get", lambda *args, **kwargs: FakeResponse())
    with pytest.raises(SourceUnavailableError, match="429"):
        fetch_feed("https://example.com/feed")


def test_arbeitnow_rejects_german_office_roles():
    job = arbeitnow_from_item(
        {
            "title": "AI / Machine Learning Engineer II",
            "company_name": "SumUp",
            "location": "Berlin, Berlin, Germany",
            "url": "https://www.arbeitnow.com/jobs/ai-berlin",
            "description": "<p>Remote-friendly Python role in Europe.</p>",
            "tags": ["Python"],
            "job_types": ["full-time"],
            "remote": True,
        },
        "Python",
        "France",
    )
    assert job is None


def test_lba_maps_structured_job():
    job = lba_from_item(
        {
            "offer": {
                "title": "Développeur Python",
                "description": "Développement d'APIs à Paris.",
                "desired_skills": ["Python"],
                "rome_codes": ["M1805"],
            },
            "workplace": {
                "name": "DINUM",
                "location": {"address": "20 AVENUE DE SEGUR 75007 PARIS"},
            },
            "apply": {"url": "https://labonnealternance.apprentissage.beta.gouv.fr/emploi/abc"},
            "contract": {"type": ["Apprentissage"]},
        },
        "Python",
        "France",
    )
    assert job is not None
    assert job.source == "la_bonne_alternance"
    assert job.company == "DINUM"


def test_lba_without_token_is_unavailable():
    adapter = LaBonneAlternanceSearchAdapter(token="")
    assert adapter.is_available is False


def test_lba_invalid_token_is_unavailable(monkeypatch):
    class FakeResponse:
        status_code = 401

        def raise_for_status(self):
            raise requests.HTTPError("401")

        def json(self):
            return {"message": "Unauthorized"}

    monkeypatch.setattr("app.services.search.adapters.la_bonne_alternance.requests.get", lambda *args, **kwargs: FakeResponse())
    adapter = LaBonneAlternanceSearchAdapter(token="invalid-token")
    with pytest.raises(SourceUnavailableError, match="rejected the API token"):
        adapter._search_jobs("Python", "France", 5)


def test_process_job_uses_discovered_payload_without_scraping(monkeypatch):
    def fail_scrape(url):
        raise AssertionError("API jobs must not scrape the listing page")

    monkeypatch.setattr(extraction_tasks, "scrape_job", fail_scrape)

    import asyncio

    result = asyncio.run(
        extraction_tasks.process_job(
            {"job_id": "feed-1", "job_try": 1},
            url="https://remotive.com/remote-jobs/python-123",
            raw_text="Build Python services for a French team.",
            discovered={
                "title": "Python Engineer",
                "company": "Acme",
                "location": "Paris",
                "source": "remotive",
                "description": "Build Python services for a French team.",
                "skills": ["Python"],
                "structured": True,
                "extraction_path": "remotive_api",
            },
        )
    )
    assert result["extraction_status"] == "complete"
    assert result["title"] == "Python Engineer"
    assert result["company"] == "Acme"


def test_discovered_payload_builds_raw_job_fields():
    raw = RawJobPosting(
        url="https://www.arbeitnow.com/jobs/x",
        title="Intern",
        company="Startup",
        location="Lyon, France",
        raw_text="Stage data engineer.",
        source="arbeitnow",
        metadata={"structured": True, "description": "Stage data engineer.", "skills": ["SQL"]},
    )
    assert raw.source == "arbeitnow"
