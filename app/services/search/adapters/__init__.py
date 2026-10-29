"""Search adapters for job discovery sources."""

from app.services.search.adapters.arbeitnow import ArbeitnowSearchAdapter
from app.services.search.adapters.france_travail import FranceTravailSearchAdapter
from app.services.search.adapters.hellowork import HelloWorkSearchAdapter
from app.services.search.adapters.indeed import IndeedSearchAdapter
from app.services.search.adapters.jobicy import JobicySearchAdapter
from app.services.search.adapters.la_bonne_alternance import LaBonneAlternanceSearchAdapter
from app.services.search.adapters.remotive import RemotiveSearchAdapter

__all__ = [
    "ArbeitnowSearchAdapter",
    "FranceTravailSearchAdapter",
    "HelloWorkSearchAdapter",
    "IndeedSearchAdapter",
    "JobicySearchAdapter",
    "LaBonneAlternanceSearchAdapter",
    "RemotiveSearchAdapter",
]
