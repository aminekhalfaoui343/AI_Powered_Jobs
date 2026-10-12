"""Read and write extracted jobs in PostgreSQL."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from sqlmodel import select

from app.db.models import ExtractedJob
from app.db.session import is_initialized, session_scope

logger = logging.getLogger(__name__)


def extracted_job_to_outcome(row: ExtractedJob) -> dict[str, Any]:
    """Match the GET /jobs/{id} payload produced from Redis/ARQ."""
    payload: dict[str, Any] = {
        "job_id": row.job_id,
        "status": row.status,
        "result": row.result or None,
    }
    if row.status == "failed":
        payload["error"] = row.error or "Extraction failed"
    return payload


def _row_from_payload(job_id: str, payload: dict[str, Any]) -> ExtractedJob:
    extraction_status = payload.get("extraction_status")
    status = "complete" if extraction_status == "complete" else "failed"
    result = {
        key: value
        for key, value in payload.items()
        if key not in {"extraction_status", "error"}
    }
    skills = result.get("skills")
    if not isinstance(skills, list):
        skills = []
    return ExtractedJob(
        job_id=job_id,
        status=status,
        url=payload.get("url") or payload.get("source_url"),
        title=payload.get("title"),
        company=payload.get("company"),
        location=payload.get("location"),
        source=payload.get("source"),
        skills=[str(skill) for skill in skills],
        result=result,
        error=None if status == "complete" else (payload.get("error") or "Extraction failed"),
        updated_at=datetime.now(timezone.utc),
    )


async def save_job_result(job_id: str, payload: dict[str, Any]) -> None:
    """Upsert one extraction result. No-op until init_db() has run."""
    if not is_initialized():
        return

    incoming = _row_from_payload(job_id, payload)
    try:
        async with session_scope() as session:
            existing = await session.get(ExtractedJob, job_id)
            if existing is None:
                session.add(incoming)
            else:
                existing.status = incoming.status
                existing.url = incoming.url
                existing.title = incoming.title
                existing.company = incoming.company
                existing.location = incoming.location
                existing.source = incoming.source
                existing.skills = incoming.skills
                existing.result = incoming.result
                existing.error = incoming.error
                existing.updated_at = incoming.updated_at
            await session.commit()
    except Exception:
        logger.exception("Could not persist extracted job job_id=%s", job_id)


async def get_extracted_job(job_id: str) -> ExtractedJob | None:
    if not is_initialized():
        return None
    async with session_scope() as session:
        return await session.get(ExtractedJob, job_id)


async def list_extracted_jobs(limit: int = 50) -> list[ExtractedJob]:
    if not is_initialized():
        return []
    statement = (
        select(ExtractedJob)
        .order_by(ExtractedJob.updated_at.desc())
        .limit(max(1, min(limit, 200)))
    )
    async with session_scope() as session:
        result = await session.exec(statement)
        return list(result.all())
