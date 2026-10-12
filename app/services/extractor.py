"""Adapter for the existing Stage B OpenRouter extractor."""

from __future__ import annotations

import logging
import re

from app.observability.langsmith import traceable
from models.job_posting import JobPosting
from models.raw_job import RawJobPosting
from pipeline.run import extract_job as existing_extract_job

logger = logging.getLogger(__name__)


@traceable(name="structured_extract_job", run_type="parser")
def try_structured_extraction(raw_job: RawJobPosting) -> JobPosting | None:
    """Build a JobPosting from scraper-provided fields when they are already complete.

    France Travail's public BFF returns title, company, location, description,
    skills, salary, and contract type. Sending that payload to an LLM is slow
    and unnecessary. Return None when required fields are missing so the LLM
    path can still run for unstructured pages.
    """
    metadata = raw_job.metadata or {}
    if not metadata.get("structured"):
        return None

    title = _text(raw_job.title)
    company = _text(raw_job.company) or "Employeur non communiqué"
    location = _text(raw_job.location) or "Non communiqué"
    description = _text(metadata.get("description")) or _concise_description(raw_job.raw_text)
    if not title or not description:
        logger.info("Structured extraction skipped; missing title or description url=%s", raw_job.url)
        return None

    skills = metadata.get("skills")
    if not isinstance(skills, list):
        skills = []
    skills = [str(skill).strip() for skill in skills if str(skill).strip()]

    job = JobPosting(
        title=title,
        company=company,
        location=location,
        description=_concise_description(description),
        skills=skills,
        experience=_text(metadata.get("experience")),
        education=_text(metadata.get("education")),
        salary=_text(metadata.get("salary")),
        contract_type=_text(metadata.get("contract_type")),
        source=raw_job.source,
        source_url=raw_job.url,
        sources=[raw_job.source] if raw_job.source else [],
        posted_date=_text(metadata.get("posted_date")),
        metadata={
            "extraction_path": metadata.get("extraction_path") or "structured",
            "offer_id": metadata.get("offer_id"),
        },
    )
    logger.info(
        "Structured extraction used; skipping LLM title=%r company=%r url=%s",
        job.title,
        job.company,
        raw_job.url,
    )
    return job


@traceable(name="extract_job", run_type="chain")
async def extract_job(raw_job: RawJobPosting) -> JobPosting:
    """Connect the queue workflow to the project's existing extractor."""
    structured = try_structured_extraction(raw_job)
    if structured is not None:
        return structured
    return await existing_extract_job(raw_job)


def _text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _concise_description(text: str, max_sentences: int = 4, max_chars: int = 800) -> str:
    collapsed = " ".join(text.split())
    if not collapsed:
        return collapsed
    sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", collapsed) if part.strip()]
    summary = " ".join(sentences[:max_sentences]) if sentences else collapsed
    return summary[:max_chars]
