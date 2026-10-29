"""Shared helpers for public JSON job feeds (no scraping of restricted sites)."""

from __future__ import annotations

import logging
import re

import requests
from bs4 import BeautifulSoup

from app.services.search.base import SourceUnavailableError

logger = logging.getLogger(__name__)

API_HEADERS = {
    "Accept": "application/json",
    "User-Agent": "AI-Powered-Jobs-PFE/1.0 (academic research; French job intelligence)",
}

_FRANCE_TOKENS = (
    "france",
    "french",
    "francais",
    "français",
    "ile-de-france",
    "île-de-france",
    "paris",
    "lyon",
    "marseille",
    "toulouse",
    "lille",
    "nantes",
    "bordeaux",
    "grenoble",
    "rennes",
    "montpellier",
    "strasbourg",
    "tours",
    "rouen",
    "dijon",
    "reims",
    "angers",
    "orleans",
    "orléans",
    "clermont-ferrand",
    "saint-etienne",
    "saint-étienne",
    "aix-en-provence",
    "le havre",
)

_REMOTE_TOKENS = ("remote", "worldwide", "anywhere", "europe", "emea", "global", "europa")

_FOREIGN_PLACE_TOKENS = (
    "germany",
    "deutschland",
    "berlin",
    "munich",
    "munchen",
    "münchen",
    "hamburg",
    "austria",
    "switzerland",
    "united states",
    "usa",
    "united kingdom",
    "ireland",
    "dublin",
    "spain",
    "madrid",
    "barcelona",
    "italy",
    "rome",
    "milan",
    "portugal",
    "netherlands",
    "amsterdam",
    "belgium",
    "brussels",
    "sweden",
    "norway",
    "denmark",
    "finland",
    "poland",
    "canada",
    "australia",
    "india",
    "brazil",
    "mexico",
    "japan",
    "austin",
    "texas",
    "london",
    "uk",
)

_GENERIC_REQUESTS = {"", "france", "remote", "anywhere", "europe", "worldwide"}


def html_to_text(value: object) -> str:
    if value is None:
        return ""
    return BeautifulSoup(str(value), "html.parser").get_text(" ", strip=True)


def fetch_feed(url: str, timeout: tuple[float, float] = (5, 25)) -> dict:
    logger.info("Fetching public job feed %s", url)
    try:
        response = requests.get(url, headers=API_HEADERS, timeout=timeout)
    except requests.Timeout as exc:
        raise SourceUnavailableError("Job feed timed out") from exc
    except requests.ConnectionError as exc:
        raise SourceUnavailableError("Job feed unreachable") from exc
    if response.status_code == 429:
        raise SourceUnavailableError("Job feed rate limited (HTTP 429)")
    if response.status_code >= 500:
        raise SourceUnavailableError(f"Job feed server error (HTTP {response.status_code})")
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError("Job feed did not return a JSON object")
    return payload


def _normalized_text(*parts: object) -> str:
    return re.sub(r"\s+", " ", " ".join(str(part or "") for part in parts)).strip().lower()


def _has_token(blob: str, token: str) -> bool:
    return re.search(rf"(?<!\w){re.escape(token)}(?!\w)", blob, flags=re.IGNORECASE) is not None


def mentions_france_market(*parts: object) -> bool:
    blob = _normalized_text(*parts)
    return any(_has_token(blob, token) for token in _FRANCE_TOKENS)


def mentions_france_specific(*parts: object) -> bool:
    return mentions_france_market(*parts)


def _place_is_foreign_specific(place: str) -> bool:
    cleaned = _normalized_text(place)
    if not cleaned or mentions_france_specific(cleaned):
        return False
    has_foreign = any(_has_token(cleaned, token) for token in _FOREIGN_PLACE_TOKENS)
    if not has_foreign:
        return False
    # Keep multi-region remote roles that include Europe; drop "Germany (Remote)" offices.
    if any(_has_token(cleaned, token) for token in ("europe", "emea", "worldwide", "anywhere", "global")):
        return False
    return True


def _place_is_remote_or_europe(place: str) -> bool:
    cleaned = _normalized_text(place)
    if not cleaned:
        return True
    if any(_has_token(cleaned, token) for token in _REMOTE_TOKENS):
        return True
    return cleaned in _GENERIC_REQUESTS


def matches_query(query: str, *parts: object) -> bool:
    blob = _normalized_text(*parts)
    tokens = [token for token in re.split(r"\W+", query.lower()) if len(token) > 2]
    if not tokens:
        return True
    return any(token in blob for token in tokens)


def matches_requested_location(requested: str | None, place: str = "", *context: object) -> bool:
    """Keep France-relevant jobs and drop foreign office locations such as Berlin."""
    if _place_is_foreign_specific(place):
        return False
    requested_clean = _normalized_text(requested or "")
    haystack = _normalized_text(place, *context)
    if requested_clean not in _GENERIC_REQUESTS:
        if requested_clean not in haystack:
            return False
        return mentions_france_specific(place, *context) or _place_is_remote_or_europe(place)
    if mentions_france_specific(place, *context):
        return True
    return _place_is_remote_or_europe(place)
