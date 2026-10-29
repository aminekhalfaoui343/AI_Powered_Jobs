"""
France Travail (formerly Pôle emploi) job detail scraper.

Detail pages are a JavaScript web component. The listing HTML does not contain
the job body; the public page loads it from:

  GET https://candidat.francetravail.fr/api-descriptifoffre/offre/{id}

That endpoint is the same BFF the website uses. Parsing the HTML shell would
only capture the "related offers" sidebar and send garbage to the LLM.
"""

from __future__ import annotations

import logging
import re
from urllib.parse import urlsplit

from models.raw_job import RawJobPosting
from scrapers.base import BaseScraper
from utils.http import fetch_json

logger = logging.getLogger(__name__)

DOMAIN_PATTERNS = ("francetravail.fr", "pole-emploi.fr")
BFF_OFFER_URL = "https://candidat.francetravail.fr/api-descriptifoffre/offre/{offer_id}"
OFFER_ID_RE = re.compile(r"/offres/recherche/detail/([^/?#]+)/?$", re.IGNORECASE)


class FranceTravailScraper(BaseScraper):
    source_name = "France Travail"

    @classmethod
    def can_handle(cls, url: str) -> bool:
        url_lower = url.lower()
        return any(domain in url_lower for domain in DOMAIN_PATTERNS)

    def scrape(self, url: str) -> RawJobPosting:
        offer_id = self.offer_id_from_url(url)
        if not offer_id:
            raise ValueError(f"Not a France Travail job detail URL: {url}")

        bff_url = BFF_OFFER_URL.format(offer_id=offer_id)
        logger.info("France Travail BFF fetch started offer_id=%s", offer_id)
        payload = fetch_json(bff_url)
        raw_job = self._raw_job_from_bff(url, offer_id, payload)
        logger.info(
            "France Travail BFF scrape complete — title=%r company=%r location=%r text_len=%d",
            raw_job.title,
            raw_job.company,
            raw_job.location,
            len(raw_job.raw_text),
        )
        return raw_job

    @staticmethod
    def offer_id_from_url(url: str) -> str | None:
        path = urlsplit(url).path
        match = OFFER_ID_RE.search(path)
        if not match:
            return None
        offer_id = match.group(1).strip()
        return offer_id or None

    def _raw_job_from_bff(self, url: str, offer_id: str, payload: dict) -> RawJobPosting:
        title = _clean(payload.get("intituleOffre"))
        description = _clean(payload.get("descriptif"))
        if not title or not description:
            raise ValueError("France Travail BFF response is missing the job title or description")

        establishment = payload.get("etablissement") if isinstance(payload.get("etablissement"), dict) else {}
        company = _clean(establishment.get("libelleEnseigne"))
        location = _clean(payload.get("lieuTravail"))
        skills = _string_list(payload.get("listeCompetence"), "libelleCompetence")
        education_items = _string_list(payload.get("listeFormation"), "libelleFormation")
        experience = _nested_text(payload.get("experienceProfil"), "experience")
        salary = _clean(payload.get("salaire"))
        contract_type = _clean(payload.get("syntheseContrat"))

        raw_text = _build_structured_text(
            title=title,
            company=company,
            location=location,
            contract_type=contract_type,
            salary=salary,
            experience=experience,
            education=education_items,
            skills=skills,
            description=description,
        )

        return RawJobPosting(
            url=url,
            title=title,
            company=company,
            location=location,
            raw_text=raw_text,
            source=self.source_name,
            metadata={
                "structured": True,
                "extraction_path": "france_travail_bff",
                "offer_id": offer_id,
                "description": description,
                "skills": skills,
                "education": education_items[0] if education_items else None,
                "experience": experience,
                "salary": salary,
                "contract_type": contract_type,
                "posted_date": _clean(payload.get("dateDerniereModification")),
            },
        )


def _clean(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _nested_text(value: object, key: str) -> str | None:
    if not isinstance(value, dict):
        return None
    return _clean(value.get(key))


def _string_list(value: object, key: str) -> list[str]:
    if not isinstance(value, list):
        return []
    items: list[str] = []
    for entry in value:
        if not isinstance(entry, dict):
            continue
        text = _clean(entry.get(key))
        if text:
            items.append(text)
    return items


def _build_structured_text(
    title: str,
    company: str | None,
    location: str | None,
    contract_type: str | None,
    salary: str | None,
    experience: str | None,
    education: list[str],
    skills: list[str],
    description: str,
) -> str:
    lines = [f"Title: {title}"]
    if company:
        lines.append(f"Company: {company}")
    if location:
        lines.append(f"Location: {location}")
    if contract_type:
        lines.append(f"Contract: {contract_type}")
    if salary:
        lines.append(f"Salary: {salary}")
    if experience:
        lines.append(f"Experience: {experience}")
    if education:
        lines.append("Education: " + "; ".join(education))
    if skills:
        lines.append("Skills: " + "; ".join(skills))
    lines.extend(["", "Description:", description])
    return "\n".join(lines)
