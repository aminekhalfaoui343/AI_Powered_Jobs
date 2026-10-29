from __future__ import annotations

from app.config import ENABLED_JOB_SOURCES
from app.services.search.adapters.arbeitnow import ArbeitnowSearchAdapter
from app.services.search.adapters.france_travail import FranceTravailSearchAdapter
from app.services.search.adapters.hellowork import HelloWorkSearchAdapter
from app.services.search.adapters.indeed import IndeedSearchAdapter
from app.services.search.adapters.jobicy import JobicySearchAdapter
from app.services.search.adapters.la_bonne_alternance import LaBonneAlternanceSearchAdapter
from app.services.search.adapters.remotive import RemotiveSearchAdapter
from app.services.search.adapters.unavailable_source import UnavailableSourceAdapter
from app.services.search.base import BaseJobSearchAdapter


SOURCE_REGISTRY: dict[str, BaseJobSearchAdapter] = {
    "france_travail": FranceTravailSearchAdapter(),
    "arbeitnow": ArbeitnowSearchAdapter(),
    "remotive": RemotiveSearchAdapter(),
    "jobicy": JobicySearchAdapter(),
    "indeed": IndeedSearchAdapter(),
    "hellowork": HelloWorkSearchAdapter(),
    "welcome_to_the_jungle": UnavailableSourceAdapter(
        "welcome_to_the_jungle", "Welcome to the Jungle", "javascript_or_restricted"
    ),
    "jobteaser": UnavailableSourceAdapter("jobteaser", "JobTeaser", "javascript_or_restricted"),
    "apec": UnavailableSourceAdapter("apec", "APEC", "public_page_or_restricted"),
    "la_bonne_alternance": LaBonneAlternanceSearchAdapter(),
}


def list_source_statuses() -> list[dict[str, object]]:
    return [
        {
            "id": source_id,
            "name": adapter.display_name or source_id,
            "enabled": source_id in ENABLED_JOB_SOURCES,
            "status": "available" if adapter.is_available else "not_supported",
            "access_type": adapter.access_type,
        }
        for source_id, adapter in SOURCE_REGISTRY.items()
    ]


def list_enabled_sources() -> list[str]:
    return [source_id for source_id in SOURCE_REGISTRY if source_id in ENABLED_JOB_SOURCES]
