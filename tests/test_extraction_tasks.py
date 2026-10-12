import asyncio

import pytest

from app.services.extractor import try_structured_extraction
from app.tasks import extraction_tasks
from models.job_posting import JobPosting
from models.raw_job import RawJobPosting


def _structured_raw_job() -> RawJobPosting:
    return RawJobPosting(
        url="https://candidat.francetravail.fr/offres/recherche/detail/214JPDD",
        title="Platform Engineer Junior",
        company="EKIMETRICS FRANCE",
        location="PARIS (75)",
        raw_text="Title: Platform Engineer Junior\nDescription: Build platform tooling.",
        source="France Travail",
        metadata={
            "structured": True,
            "extraction_path": "france_travail_bff",
            "description": "Build platform tooling for Data and AI products.",
            "skills": ["Kubernetes", "Terraform"],
            "contract_type": "CDI - Contrat travail",
            "salary": "42000 Euros",
        },
    )


def test_structured_extraction_skips_llm():
    job = try_structured_extraction(_structured_raw_job())

    assert job is not None
    assert job.title == "Platform Engineer Junior"
    assert job.company == "EKIMETRICS FRANCE"
    assert "Kubernetes" in job.skills
    assert job.metadata["extraction_path"] == "france_travail_bff"


def test_unstructured_raw_job_does_not_skip_llm():
    raw = RawJobPosting(
        url="https://example.com/job",
        title="DevOps",
        company=None,
        location=None,
        raw_text="A long enough job description that still needs an LLM. " * 4,
        source="example",
    )

    assert try_structured_extraction(raw) is None


@pytest.mark.asyncio
async def test_process_job_skips_llm_for_structured_france_travail(monkeypatch):
    llm_calls = {"count": 0}

    async def fail_if_llm(raw_job):
        llm_calls["count"] += 1
        raise AssertionError("LLM must not run when structured France Travail fields exist")

    monkeypatch.setattr(extraction_tasks, "scrape_job", lambda url: _structured_raw_job())
    monkeypatch.setattr(extraction_tasks, "extract_job", fail_if_llm)

    result = await extraction_tasks.process_job({"job_id": "abc", "job_try": 1}, url="https://example.com/job")

    assert result["extraction_status"] == "complete"
    assert result["title"] == "Platform Engineer Junior"
    assert result["company"] == "EKIMETRICS FRANCE"
    assert llm_calls["count"] == 0


@pytest.mark.asyncio
async def test_process_job_returns_failed_result_instead_of_blocking(monkeypatch):
    def boom(url):
        raise ValueError("Could not extract job content")

    monkeypatch.setattr(extraction_tasks, "scrape_job", boom)

    result = await extraction_tasks.process_job(
        {"job_id": "abc", "job_try": 2},
        url="https://candidat.francetravail.fr/offres/recherche/detail/214JPDD",
    )

    assert result["extraction_status"] == "failed"
    assert "Could not extract job content" in result["error"]


@pytest.mark.asyncio
async def test_process_job_retries_scrape_timeout(monkeypatch):
    def hang(url):
        raise TimeoutError("Job page scrape timed out after 25s")

    monkeypatch.setattr(extraction_tasks, "scrape_job", hang)

    with pytest.raises(RuntimeError, match="timed out"):
        await extraction_tasks.process_job({"job_id": "abc", "job_try": 1}, url="https://example.com/job")


@pytest.mark.asyncio
async def test_one_failed_job_does_not_prevent_other_jobs(monkeypatch):
    async def process(url):
        if "bad" in url:
            return await extraction_tasks.process_job({"job_id": "bad", "job_try": 2}, url=url)
        return await extraction_tasks.process_job({"job_id": "good", "job_try": 1}, url=url)

    def scrape(url):
        if "bad" in url:
            raise ValueError("blocked page")
        return _structured_raw_job()

    monkeypatch.setattr(extraction_tasks, "scrape_job", scrape)

    failed, ok = await asyncio.gather(process("https://example.com/bad"), process("https://example.com/good"))

    assert failed["extraction_status"] == "failed"
    assert ok["extraction_status"] == "complete"
    assert ok["title"] == "Platform Engineer Junior"


@pytest.mark.asyncio
async def test_process_job_uses_llm_when_unstructured(monkeypatch):
    raw = RawJobPosting(
        url="https://example.com/job",
        title="DevOps",
        company="Acme",
        location="Paris",
        raw_text="A long enough job description that still needs an LLM. " * 4,
        source="example",
    )
    extracted = JobPosting(
        title="DevOps",
        company="Acme",
        location="Paris",
        description="Operate cloud platforms.",
        skills=["AWS"],
    )

    async def fake_extract(raw_job):
        return extracted

    monkeypatch.setattr(extraction_tasks, "scrape_job", lambda url: raw)
    monkeypatch.setattr(extraction_tasks, "extract_job", fake_extract)

    result = await extraction_tasks.process_job({"job_id": "abc", "job_try": 1}, url="https://example.com/job")

    assert result["extraction_status"] == "complete"
    assert result["title"] == "DevOps"
    assert result["skills"] == ["AWS"]
