import asyncio
from unittest.mock import Mock

import pytest

from app.services import extractor as service_extractor
from extraction import openrouter_extractor as extractor
from models.job_posting import JobPosting
from models.raw_job import RawJobPosting


@pytest.fixture
def sample_raw_job() -> RawJobPosting:
    return RawJobPosting(
        url="https://example.com/job",
        title="Python Developer",
        company="Example Corp",
        location="Paris",
        raw_text="This is a long enough job description to be processed by the LLM. " * 4,
        source="example",
    )


@pytest.fixture
def valid_job() -> JobPosting:
    return JobPosting(
        title="Python Developer",
        company="Example Corp",
        location="Paris",
        description="Build backend services.",
        skills=["Python", "FastAPI"],
        experience="2+ years",
        education=None,
        salary=None,
        contract_type="CDI",
    )


@pytest.mark.asyncio
async def test_service_extractor_awaits_async_pipeline(monkeypatch, sample_raw_job, valid_job):
    async def fake_pipeline_extract(raw_job):
        assert raw_job.url == sample_raw_job.url
        return valid_job

    monkeypatch.setattr(service_extractor, "existing_extract_job", fake_pipeline_extract)

    result = await service_extractor.extract_job(sample_raw_job)

    assert result.title == "Python Developer"
    assert result.company == "Example Corp"


@pytest.mark.asyncio
async def test_successful_llm_call_no_retry(monkeypatch, sample_raw_job, valid_job):
    calls = {"count": 0}

    def fake_extract(raw_job):
        calls["count"] += 1
        assert raw_job.url == sample_raw_job.url
        return valid_job

    monkeypatch.setattr(extractor, "extract_job_posting", fake_extract)

    result = await extractor.extract_job_posting_with_retry(sample_raw_job)

    assert result.title == "Python Developer"
    assert calls["count"] == 1


@pytest.mark.asyncio
async def test_temporary_failure_retries(monkeypatch, sample_raw_job, valid_job):
    calls = {"count": 0}

    def fake_extract(raw_job):
        calls["count"] += 1
        if calls["count"] < 3:
            raise ConnectionError("temporary provider issue")
        return valid_job

    monkeypatch.setattr(extractor, "extract_job_posting", fake_extract)
    monkeypatch.setattr(extractor, "LLM_MAX_TRIES", 3)

    result = await extractor.extract_job_posting_with_retry(sample_raw_job)

    assert result.title == "Python Developer"
    assert calls["count"] == 3


@pytest.mark.asyncio
async def test_timeout_retries(monkeypatch, sample_raw_job, valid_job):
    calls = {"count": 0}

    def fake_extract(raw_job):
        calls["count"] += 1
        if calls["count"] < 3:
            raise TimeoutError("request timed out")
        return valid_job

    monkeypatch.setattr(extractor, "extract_job_posting", fake_extract)
    monkeypatch.setattr(extractor, "LLM_MAX_TRIES", 3)

    result = await extractor.extract_job_posting_with_retry(sample_raw_job)

    assert result.title == "Python Developer"
    assert calls["count"] == 3


@pytest.mark.asyncio
async def test_max_retries_reached_raises_failure(monkeypatch, sample_raw_job):
    calls = {"count": 0}

    def fake_extract(raw_job):
        calls["count"] += 1
        raise ConnectionError("provider unavailable")

    monkeypatch.setattr(extractor, "extract_job_posting", fake_extract)
    monkeypatch.setattr(extractor, "LLM_MAX_TRIES", 3)

    with pytest.raises(ConnectionError, match="provider unavailable"):
        await extractor.extract_job_posting_with_retry(sample_raw_job)

    assert calls["count"] == 3


@pytest.mark.asyncio
async def test_non_retryable_error_does_not_retry(monkeypatch, sample_raw_job):
    calls = {"count": 0}

    def fake_extract(raw_job):
        calls["count"] += 1
        raise ValueError("LLM returned invalid JSON")

    monkeypatch.setattr(extractor, "extract_job_posting", fake_extract)

    with pytest.raises(ValueError, match="LLM returned invalid JSON"):
        await extractor.extract_job_posting_with_retry(sample_raw_job)

    assert calls["count"] == 1


@pytest.mark.asyncio
async def test_invalid_response_is_not_retried(monkeypatch, sample_raw_job):
    calls = {"count": 0}

    def fake_extract(raw_job):
        calls["count"] += 1
        raise ValueError("missing required fields")

    monkeypatch.setattr(extractor, "extract_job_posting", fake_extract)

    with pytest.raises(ValueError, match="missing required fields"):
        await extractor.extract_job_posting_with_retry(sample_raw_job)

    assert calls["count"] == 1


@pytest.mark.asyncio
async def test_concurrency_limit_is_respected():
    sem = asyncio.Semaphore(extractor.LLM_MAX_CONCURRENT)
    active = 0
    peak = 0

    async def worker(i: int):
        nonlocal active, peak
        async with sem:
            active += 1
            peak = max(peak, active)
            await asyncio.sleep(0.05)
            active -= 1

    await asyncio.gather(*(worker(i) for i in range(10)))

    assert peak <= extractor.LLM_MAX_CONCURRENT
    assert peak == extractor.LLM_MAX_CONCURRENT
