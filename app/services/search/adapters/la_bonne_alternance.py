"""La bonne alternance job search. Free token required; no HTML scraping."""

from __future__ import annotations

import asyncio
import logging
import re
from urllib.parse import urlencode

import requests

from app.config import LBA_API_BASE_URL, LBA_API_TOKEN
from app.services.search.base import BaseJobSearchAdapter, SourceUnavailableError
from app.services.search.feeds import (
    API_HEADERS,
    html_to_text,
    matches_query,
    matches_requested_location,
)
from models.discovered_job import DiscoveredJob

logger = logging.getLogger(__name__)

SEARCH_PATH = "/job/v1/search"
_ROME_BY_TOKEN = {
    "python": "M1805",
    "java": "M1805",
    "javascript": "M1805",
    "typescript": "M1805",
    "developer": "M1805",
    "developpeur": "M1805",
    "développeur": "M1805",
    "devops": "M1802",
    "kubernetes": "M1802",
    "cloud": "M1802",
    "data": "M1805",
    "cyber": "M1802",
    "reseau": "M1801",
    "réseau": "M1801",
    "admin": "M1801",
}


class LaBonneAlternanceSearchAdapter(BaseJobSearchAdapter):
    source_name = "la_bonne_alternance"
    display_name = "La bonne alternance"
    access_type = "free_api_token"

    def __init__(self, token: str | None = None, base_url: str | None = None):
        self._token = (LBA_API_TOKEN if token is None else token).strip()
        self._base_url = (base_url or LBA_API_BASE_URL).rstrip("/")
        self.is_available = bool(self._token)
        self.access_type = "free_api_token" if self.is_available else "free_api_token_required"

    async def search_jobs(
        self, query: str, location: str | None = None, limit: int = 20
    ) -> list[DiscoveredJob]:
        return await asyncio.to_thread(self._search_jobs, query, location, limit)

    def _search_jobs(self, query: str, location: str | None, limit: int) -> list[DiscoveredJob]:
        if not query or not query.strip():
            raise ValueError("Search query cannot be blank")
        if limit <= 0:
            return []
        if not self._token:
            raise SourceUnavailableError(
                "La bonne alternance requires a free API token. "
                "Create one at https://api.apprentissage.beta.gouv.fr/compte/profil "
                "and set LBA_API_TOKEN."
            )

        params: dict[str, str] = {}
        romes = _romes_for_query(query)
        if romes:
            params["romes"] = ",".join(romes)
        url = f"{self._base_url}{SEARCH_PATH}"
        if params:
            url = f"{url}?{urlencode(params)}"
        payload = _fetch_lba(url, self._token)
        rows = payload.get("jobs")
        if not isinstance(rows, list):
            return []

        jobs: list[DiscoveredJob] = []
        seen: set[str] = set()
        for item in rows:
            job = _from_item(item, query.strip(), location)
            if job is None or job.url in seen:
                continue
            seen.add(job.url)
            jobs.append(job)
            if len(jobs) >= limit:
                break
        logger.info("La bonne alternance discovery completed jobs_found=%d", len(jobs))
        return jobs


def _romes_for_query(query: str) -> list[str]:
    blob = query.lower()
    romes: list[str] = []
    for token, code in _ROME_BY_TOKEN.items():
        if re.search(rf"(?<!\w){re.escape(token)}(?!\w)", blob) and code not in romes:
            romes.append(code)
    return romes


def _fetch_lba(url: str, token: str) -> dict:
    headers = {**API_HEADERS, "Authorization": f"Bearer {token}"}
    try:
        response = requests.get(url, headers=headers, timeout=(5, 25))
    except requests.Timeout as exc:
        raise SourceUnavailableError("La bonne alternance timed out") from exc
    except requests.ConnectionError as exc:
        raise SourceUnavailableError("La bonne alternance unreachable") from exc
    if response.status_code in {401, 403}:
        raise SourceUnavailableError(
            "La bonne alternance rejected the API token. Create a valid key at "
            "https://api.apprentissage.beta.gouv.fr/compte/profil"
        )
    if response.status_code == 429:
        raise SourceUnavailableError("La bonne alternance rate limited the request (HTTP 429)")
    if response.status_code >= 500:
        raise SourceUnavailableError(f"La bonne alternance server error (HTTP {response.status_code})")
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError("La bonne alternance did not return a JSON object")
    return payload


def _from_item(item: object, query: str, location: str | None) -> DiscoveredJob | None:
    if not isinstance(item, dict):
        return None
    offer = item.get("offer") if isinstance(item.get("offer"), dict) else {}
    workplace = item.get("workplace") if isinstance(item.get("workplace"), dict) else {}
    apply = item.get("apply") if isinstance(item.get("apply"), dict) else {}
    contract = item.get("contract") if isinstance(item.get("contract"), dict) else {}
    place_info = workplace.get("location") if isinstance(workplace.get("location"), dict) else {}

    title = str(offer.get("title") or "").strip()
    company = str(workplace.get("name") or workplace.get("legal_name") or "").strip()
    place = str(place_info.get("address") or "").strip()
    url = str(apply.get("url") or "").strip()
    description = html_to_text(offer.get("description"))
    skills = offer.get("desired_skills") if isinstance(offer.get("desired_skills"), list) else []
    contract_types = contract.get("type") if isinstance(contract.get("type"), list) else []
    if not title or not url:
        return None
    if not matches_query(query, title, company, description, place, " ".join(str(skill) for skill in skills)):
        return None
    if not matches_requested_location(location, place, title, description):
        return None
    return DiscoveredJob(
        title=title[:200],
        company=company or None,
        location=place or location or "France",
        description=description or None,
        url=url,
        source="la_bonne_alternance",
        metadata={
            "structured": True,
            "extraction_path": "la_bonne_alternance_api",
            "skills": [str(skill) for skill in skills if str(skill).strip()],
            "contract_type": ", ".join(str(value) for value in contract_types if value) or None,
            "rome_codes": offer.get("rome_codes") if isinstance(offer.get("rome_codes"), list) else [],
        },
    )
