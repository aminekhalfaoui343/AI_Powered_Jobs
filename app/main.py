"""FastAPI entry point for queueing job extraction tasks."""

from __future__ import annotations
import logging
from contextlib import asynccontextmanager
from urllib.parse import urlparse

from sqlalchemy.exc import SQLAlchemyError
from arq import create_pool
from arq.connections import ArqRedis
from arq.jobs import Job
from fastapi import FastAPI, HTTPException, Query, Request, status
from pydantic import BaseModel, Field, model_validator
from redis.exceptions import RedisError

from app.config import REDIS_SETTINGS
from app.db.repository import extracted_job_to_outcome, get_extracted_job, list_extracted_jobs
from app.db.session import close_db, init_db, ping_db
from app.observability.langsmith import configure_langsmith
from app.services.arq_results import read_job_outcome
from app.services.search.dedupe import deduplicate_discovered_jobs
from app.services.search.registry import list_source_statuses
from app.services.search.search_service import JobSearchService
from models.search_request import JobSearchRequest

logger = logging.getLogger(__name__)


class JobRequest(BaseModel):
    """Payload accepted by POST /jobs."""

    url: str | None = None
    raw_text: str | None = Field(default=None, min_length=50)

    @model_validator(mode="after")
    def require_one_input(self) -> "JobRequest":
        if not self.url and not self.raw_text:
            raise ValueError("Provide either a job URL or raw_text")
        if self.url:
            parsed = urlparse(self.url)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                raise ValueError("url must be a valid HTTP or HTTPS URL")
        return self


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create Redis and PostgreSQL connections and close them on shutdown."""
    try:
        app.state.redis = await create_pool(REDIS_SETTINGS)
        await app.state.redis.ping()
        logger.info("Connected to Redis")
        configure_langsmith()
    except RedisError as exc:
        logger.error("Could not connect to Redis: %s", exc)
        raise RuntimeError("Redis is unavailable. Start Redis and restart FastAPI") from exc

    try:
        await init_db()
    except (SQLAlchemyError, OSError) as exc:
        await app.state.redis.close()
        logger.error("Could not connect to PostgreSQL: %s", exc)
        raise RuntimeError("PostgreSQL is unavailable. Start Postgres and restart FastAPI") from exc

    yield
    await close_db()
    await app.state.redis.close()


app = FastAPI(title="AI Job Extraction Queue", lifespan=lifespan)


@app.get("/health")
async def health(request: Request) -> dict[str, str]:
    """Report whether the API can reach Redis and PostgreSQL."""
    try:
        await request.app.state.redis.ping()
    except RedisError as exc:
        logger.error("Redis health check failed: %s", exc)
        raise HTTPException(status_code=503, detail="Redis unavailable") from exc
    try:
        await ping_db()
    except Exception as exc:
        logger.error("PostgreSQL health check failed: %s", exc)
        raise HTTPException(status_code=503, detail="PostgreSQL unavailable") from exc
    return {"status": "ok", "redis": "ok", "postgres": "ok"}


@app.post("/jobs", status_code=status.HTTP_202_ACCEPTED)
async def submit_job(payload: JobRequest, request: Request) -> dict[str, str]:
    """Queue work and return without waiting for scraping or OpenRouter extraction."""
    logger.info("Job received")
    redis: ArqRedis = request.app.state.redis
    try:
        job = await redis.enqueue_job(
            "process_job",
            url=payload.url,
            raw_text=payload.raw_text,
        )
    except RedisError as exc:
        logger.error("Job could not be queued: %s", exc)
        raise HTTPException(status_code=503, detail="Redis unavailable") from exc

    if job is None:
        raise HTTPException(status_code=409, detail="Job was not queued")

    logger.info("Job queued job_id=%s", job.job_id)
    return {"message": "Job successfully queued", "job_id": job.job_id}


@app.post("/jobs/search", status_code=status.HTTP_202_ACCEPTED)
async def search_jobs(payload: JobSearchRequest, request: Request) -> dict:
    """Discover multiple jobs from a supported source and enqueue each URL into the existing ARQ pipeline."""
    redis: ArqRedis = request.app.state.redis
    service = JobSearchService()

    try:
        search_result = await service.search(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    unique_jobs, duplicates_skipped = deduplicate_discovered_jobs(search_result.jobs)
    enqueued = 0
    errors = []
    queued_jobs = []

    for job in unique_jobs:
        try:
            arq_job = await redis.enqueue_job("process_job", url=job.url)
        except RedisError as exc:
            logger.error("Failed to enqueue discovered job %s: %s", job.url, exc)
            errors.append({"url": job.url, "error": "redis unavailable"})
            continue

        if arq_job is None:
            logger.warning("ARQ rejected discovered job %s", job.url)
            errors.append({"url": job.url, "error": "not queued"})
            continue

        enqueued += 1
        queued_jobs.append(
            {
                "job_id": arq_job.job_id,
                "status": "queued",
                "result": {
                    "title": job.title,
                    "company": job.company,
                    "location": job.location,
                    "description": job.description,
                    "source": job.source,
                    "url": job.url,
                },
            }
        )

    source_errors = [
        {"source": source, "error": result["error"]}
        for source, result in search_result.sources.items()
        if result.get("status") != "success" and result.get("error")
    ]

    return {
        "query": payload.query,
        "sources_used": list(search_result.sources),
        "sources": search_result.sources,
        "jobs_discovered": len(search_result.jobs),
        "jobs_enqueued": enqueued,
        "jobs": queued_jobs,
        "duplicates_skipped": duplicates_skipped,
        "status": "processing",
        "errors": source_errors + errors,
    }


@app.get("/sources")
async def get_sources() -> list[dict[str, object]]:
    """Return configured source capabilities for the frontend and operators."""
    return list_source_statuses()


@app.get("/jobs")
async def list_jobs(limit: int = Query(default=50, ge=1, le=200)) -> dict:
    """Return extracted jobs persisted in PostgreSQL, newest first."""
    rows = await list_extracted_jobs(limit)
    return {"jobs": [extracted_job_to_outcome(row) for row in rows]}


@app.get("/jobs/{job_id}")
async def get_job_result(job_id: str, request: Request) -> dict:
    """Return the live ARQ status, then the PostgreSQL copy if Redis expired."""
    try:
        job = Job(job_id, request.app.state.redis)
        outcome = await read_job_outcome(job)
    except RedisError as exc:
        logger.error("Could not read job result job_id=%s: %s", job_id, exc)
        raise HTTPException(status_code=503, detail="Redis unavailable") from exc

    if outcome.get("status") != "not_found":
        return outcome

    stored = await get_extracted_job(job_id)
    if stored is not None:
        return extracted_job_to_outcome(stored)
    raise HTTPException(status_code=404, detail="Job not found")