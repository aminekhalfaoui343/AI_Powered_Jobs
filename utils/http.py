"""Shared HTTP helpers for all scrapers."""

import logging

import requests

logger = logging.getLogger(__name__)

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
}

DEFAULT_TIMEOUT = 15
JSON_TIMEOUT = (5, 20)


def fetch_json(url: str, timeout: float | tuple[float, float] = JSON_TIMEOUT) -> dict:
    """Fetch a JSON object with a connect/read timeout.

    Raises:
        requests.HTTPError: non-2xx response
        requests.Timeout: request timed out
        requests.RequestException: network / connection errors
        ValueError: empty or non-object JSON
    """
    logger.info("Fetching JSON: %s", url)
    response = requests.get(
        url,
        headers={**DEFAULT_HEADERS, "Accept": "application/json"},
        timeout=timeout,
    )
    response.raise_for_status()
    try:
        payload = response.json()
    except ValueError as exc:
        raise ValueError("Response was not valid JSON") from exc
    if not isinstance(payload, dict):
        raise ValueError("JSON response was not an object")
    logger.info("Fetched JSON keys=%s (HTTP %s)", sorted(payload), response.status_code)
    return payload


def fetch_html(url: str) -> str:
    """
    Fetch a page with requests.

    Raises:
        requests.HTTPError: non-2xx response
        requests.Timeout: request timed out
        requests.RequestException: network / connection errors
    """
    logger.info("Fetching URL: %s", url)
    response = requests.get(
        url,
        headers=DEFAULT_HEADERS,
        timeout=DEFAULT_TIMEOUT,
    )
    response.raise_for_status()

    if not response.text or not response.text.strip():
        raise ValueError("Empty HTML response")

    logger.info("Fetched %d characters (HTTP %s)", len(response.text), response.status_code)
    return response.text
