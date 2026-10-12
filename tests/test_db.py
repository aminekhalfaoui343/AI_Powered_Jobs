from contextlib import asynccontextmanager

import pytest

from app.db.repository import (
    extracted_job_to_outcome,
    get_extracted_job,
    list_extracted_jobs,
    save_job_result,
)
from app.db.session import close_db, init_db
from app.tasks import extraction_tasks
from models.raw_job import RawJobPosting


@asynccontextmanager
async def memory_db():
    await close_db()
    await init_db("sqlite+aiosqlite:///:memory:")
    try:
        yield
    finally:
        await close_db()


@pytest.mark.asyncio
async def test_save_and_get_complete_job():
    async with memory_db():
        await save_job_result(
            "job-1",
            {
                "extraction_status": "complete",
                "title": "Platform Engineer",
                "company": "Acme",
                "location": "Paris",
                "source": "France Travail",
                "url": "https://example.com/job",
                "skills": ["Kubernetes"],
                "description": "Build platforms.",
            },
        )

        row = await get_extracted_job("job-1")
        assert row is not None
        assert row.status == "complete"
        assert row.title == "Platform Engineer"
        assert row.skills == ["Kubernetes"]

        outcome = extracted_job_to_outcome(row)
        assert outcome["job_id"] == "job-1"
        assert outcome["status"] == "complete"
        assert outcome["result"]["company"] == "Acme"
        assert "error" not in outcome


@pytest.mark.asyncio
async def test_save_failed_job_and_upsert():
    async with memory_db():
        await save_job_result(
            "job-2",
            {
                "extraction_status": "failed",
                "error": "scrape timed out",
                "url": "https://example.com/bad",
            },
        )
        row = await get_extracted_job("job-2")
        assert row is not None
        assert row.status == "failed"
        assert extracted_job_to_outcome(row)["error"] == "scrape timed out"

        await save_job_result(
            "job-2",
            {
                "extraction_status": "complete",
                "title": "Recovered",
                "company": "Acme",
                "url": "https://example.com/bad",
                "skills": [],
            },
        )
        row = await get_extracted_job("job-2")
        assert row is not None
        assert row.status == "complete"
        assert row.title == "Recovered"


@pytest.mark.asyncio
async def test_list_jobs_newest_first():
    async with memory_db():
        await save_job_result("old", {"extraction_status": "complete", "title": "Old", "skills": []})
        await save_job_result("new", {"extraction_status": "complete", "title": "New", "skills": []})

        rows = await list_extracted_jobs(limit=10)
        assert {row.job_id for row in rows} == {"new", "old"}
        assert rows[0].updated_at >= rows[1].updated_at


@pytest.mark.asyncio
async def test_missing_job_returns_none():
    async with memory_db():
        assert await get_extracted_job("missing") is None


@pytest.mark.asyncio
async def test_process_job_persists_complete_result(monkeypatch):
    raw = RawJobPosting(
        url="https://example.com/job",
        title="Platform Engineer Junior",
        company="EKIMETRICS FRANCE",
        location="PARIS (75)",
        raw_text="Title: Platform Engineer Junior",
        source="France Travail",
        metadata={
            "structured": True,
            "description": "Build platform tooling.",
            "skills": ["Kubernetes"],
        },
    )
    monkeypatch.setattr(extraction_tasks, "scrape_job", lambda url: raw)

    async with memory_db():
        result = await extraction_tasks.process_job(
            {"job_id": "abc", "job_try": 1},
            url="https://example.com/job",
        )
        stored = await get_extracted_job("abc")

    assert result["extraction_status"] == "complete"
    assert stored is not None
    assert stored.title == "Platform Engineer Junior"
    assert stored.status == "complete"
