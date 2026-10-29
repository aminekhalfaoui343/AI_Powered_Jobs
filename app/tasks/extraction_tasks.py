"""ARQ tasks for the scrape -> OpenRouter extraction workflow."""

from __future__ import annotations

import asyncio
import logging
import time

import requests

from models.raw_job import RawJobPosting

from app.config import ARQ_MAX_TRIES, LLM_MAX_CONCURRENT, SCRAPE_TIMEOUT_SECONDS
from app.db.repository import save_job_result
from app.observability.langsmith import configure_langsmith
from app.services.extractor import extract_job, try_structured_extraction
from app.services.scraper import scrape_job

configure_langsmith()

logger = logging.getLogger(__name__)

_LLM_ACTIVE_JOBS = 0
_LLM_JOBS_LOCK = asyncio.Lock()
_LLM_CONCURRENCY_SEMAPHORE = asyncio.Semaphore(LLM_MAX_CONCURRENT)

# The queue itself remains Redis/ARQ-driven; this semaphore prevents all worker
# threads from issuing simultaneous LLM requests beyond the configured cap.


class LLMConcurrencyLimit:
    """Guard the LLM worker pool so the queue never exceeds the configured limit."""

    async def __aenter__(self) -> "LLMConcurrencyLimit":
        global _LLM_ACTIVE_JOBS
        async with _LLM_JOBS_LOCK:
            _LLM_ACTIVE_JOBS += 1
            logger.info("Active LLM jobs: %s/%s", _LLM_ACTIVE_JOBS, LLM_MAX_CONCURRENT)
        await _LLM_CONCURRENCY_SEMAPHORE.acquire()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        global _LLM_ACTIVE_JOBS
        _LLM_CONCURRENCY_SEMAPHORE.release()
        async with _LLM_JOBS_LOCK:
            _LLM_ACTIVE_JOBS -= 1
            logger.info("Active LLM jobs: %s/%s", max(_LLM_ACTIVE_JOBS, 0), LLM_MAX_CONCURRENT)


def llm_concurrency_limit() -> LLMConcurrencyLimit:
    return LLMConcurrencyLimit()


def _is_retryable_process_error(exc: BaseException) -> bool:
    if isinstance(exc, (TimeoutError, asyncio.TimeoutError, ConnectionError, OSError)):
        return True
    if isinstance(exc, (requests.Timeout, requests.ConnectionError)):
        return True
    if isinstance(exc, requests.HTTPError) and exc.response is not None:
        return 500 <= exc.response.status_code < 600
    status_code = getattr(exc, "status_code", None)
    if isinstance(status_code, int) and (status_code == 429 or 500 <= status_code < 600):
        return True
    message = str(exc).lower()
    return "timed out" in message or "temporarily" in message or "rate limit" in message


def _failed_payload(url: str | None, error: BaseException, raw_job: RawJobPosting | None = None) -> dict:
    payload = {
        "extraction_status": "failed",
        "error": str(error),
        "url": url or (raw_job.url if raw_job else None),
        "source": raw_job.source if raw_job else None,
        "title": raw_job.title if raw_job else None,
        "company": raw_job.company if raw_job else None,
        "location": raw_job.location if raw_job else None,
    }
    return payload


def _success_payload(extracted_job, url: str | None) -> dict:
    payload = extracted_job.model_dump(mode="json")
    payload["url"] = extracted_job.source_url or url
    payload["extraction_status"] = "complete"
    return payload


async def process_job(
    ctx: dict,
    url: str | None = None,
    raw_text: str | None = None,
    discovered: dict | None = None,
):
    """Process one queued URL or one already-scraped text payload.

    One failed listing must not block the rest of the batch. Transient scrape
    errors can be retried by ARQ; extraction failures are returned as a failed
    result so the queue keeps moving.
    """
    job_id = ctx.get("job_id", "unknown")
    job_try = int(ctx.get("job_try") or 1)
    logger.info("Worker started processing job_id=%s try=%s/%s", job_id, job_try, ARQ_MAX_TRIES)

    if not url and not raw_text:
        raise ValueError("A job URL or raw job text is required")

    raw_job: RawJobPosting | None = None
    try:
        if isinstance(discovered, dict) and (raw_text or discovered.get("description")):
            text = raw_text or str(discovered.get("description") or "")
            raw_job = RawJobPosting(
                url=url or str(discovered.get("url") or "submitted-text"),
                title=discovered.get("title"),
                company=discovered.get("company"),
                location=discovered.get("location"),
                raw_text=text,
                source=str(discovered.get("source") or "api"),
                metadata={**discovered, "structured": True},
            )
            logger.info("Using discovered API payload job_id=%s source=%s", job_id, raw_job.source)
        elif url:
            logger.info("Scraping started job_id=%s url=%s", job_id, url)
            scrape_started_at = time.perf_counter()
            try:
                raw_job = await asyncio.wait_for(
                    asyncio.to_thread(scrape_job, url),
                    timeout=SCRAPE_TIMEOUT_SECONDS,
                )
            except asyncio.TimeoutError as exc:
                raise TimeoutError(
                    f"Job page scrape timed out after {SCRAPE_TIMEOUT_SECONDS}s"
                ) from exc
            logger.info(
                "Scraping completed job_id=%s duration=%.2fs text_len=%s",
                job_id,
                time.perf_counter() - scrape_started_at,
                len(raw_job.raw_text),
            )
        else:
            raw_job = RawJobPosting(
                url="submitted-text",
                title=None,
                company=None,
                location=None,
                raw_text=raw_text or "",
                source="submitted-text",
            )
            logger.info("Using submitted raw text job_id=%s", job_id)

        structured_job = try_structured_extraction(raw_job)
        extraction_started_at = time.perf_counter()
        if structured_job is not None:
            logger.info("AI extraction skipped; structured fields present job_id=%s", job_id)
            extracted_job = structured_job
        else:
            logger.info("AI extraction started job_id=%s", job_id)
            async with llm_concurrency_limit():
                extracted_job = await extract_job(raw_job)
            logger.info(
                "AI extraction completed job_id=%s duration=%.2fs",
                job_id,
                time.perf_counter() - extraction_started_at,
            )
        logger.info("Job finished job_id=%s", job_id)
        payload = _success_payload(extracted_job, url)
        await save_job_result(job_id, payload)
        return payload
    except Exception as exc:
        retryable = _is_retryable_process_error(exc)
        if retryable and job_try < ARQ_MAX_TRIES:
            logger.warning(
                "Job failed retryably job_id=%s try=%s/%s url=%s error=%s",
                job_id,
                job_try,
                ARQ_MAX_TRIES,
                url,
                exc,
            )
            # Re-raise a pickle-safe error. OpenAI APIStatusError cannot be
            # unpickled later by GET /jobs/{id}.
            raise RuntimeError(f"{type(exc).__name__}: {exc}") from exc
        logger.exception("Job failed job_id=%s url=%s; returning failed result", job_id, url)
        # Never let provider exceptions bubble to ARQ pickle; they cannot be
        # reconstructed later when the API reads GET /jobs/{id}.
        payload = _failed_payload(url, exc, raw_job)
        await save_job_result(job_id, payload)
        return payload
