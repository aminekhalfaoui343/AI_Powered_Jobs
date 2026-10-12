from __future__ import annotations

from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
import re

from models.discovered_job import DiscoveredJob


def normalize_url(url: str) -> str:
    """Normalize a discovered job URL for deduplication while keeping the main destination stable."""
    parsed = urlsplit(url)
    query_items = []
    for key, value in parse_qsl(parsed.query, keep_blank_values=True):
        key_lower = key.lower()
        if key_lower.startswith("utm") or key_lower in {"gclid", "fbclid", "mc_cid", "mc_eid"}:
            continue
        query_items.append((key, value))
    cleaned_query = urlencode(query_items, doseq=True)
    cleaned_path = parsed.path.rstrip("/") or "/"
    return urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), cleaned_path, cleaned_query, ""))


def deduplicate_discovered_jobs(jobs: list[DiscoveredJob]) -> tuple[list[DiscoveredJob], int]:
    """Remove duplicate URLs or matching listing metadata while preserving sources."""
    unique_jobs: list[DiscoveredJob] = []
    seen_urls: set[str] = set()
    seen_metadata: dict[tuple[str, str, str], int] = {}
    skipped = 0

    for job in jobs:
        normalized = normalize_url(job.url)
        metadata_key = (
            _normalize_text(job.title),
            _normalize_text(job.company),
            _normalize_text(job.location),
        )
        if normalized in seen_urls:
            existing_index = next(index for index, item in enumerate(unique_jobs) if item.url == normalized)
            _merge_sources(unique_jobs[existing_index], job)
            skipped += 1
            continue
        if all(metadata_key) and metadata_key in seen_metadata:
            _merge_sources(unique_jobs[seen_metadata[metadata_key]], job)
            skipped += 1
            continue
        seen_urls.add(normalized)
        unique_jobs.append(job.model_copy(update={"url": normalized, "sources": list(job.sources)}))
        if all(metadata_key):
            seen_metadata[metadata_key] = len(unique_jobs) - 1

    return unique_jobs, skipped


def _normalize_text(value: str | None) -> str:
    return re.sub(r"\s+", " ", (value or "").lower()).strip()


def _merge_sources(target: DiscoveredJob, duplicate: DiscoveredJob) -> None:
    for source in [*duplicate.sources, duplicate.source]:
        if source not in target.sources:
            target.sources.append(source)
