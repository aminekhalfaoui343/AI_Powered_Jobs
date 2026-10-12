"""Search adapters for job discovery sources."""

from app.services.search.adapters.example_source import FranceTravailSearchAdapter
from app.services.search.adapters.hellowork import HelloWorkSearchAdapter
from app.services.search.adapters.indeed import IndeedSearchAdapter

__all__ = ["FranceTravailSearchAdapter", "HelloWorkSearchAdapter", "IndeedSearchAdapter"]
