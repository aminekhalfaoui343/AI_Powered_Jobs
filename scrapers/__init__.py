"""Website-specific scrapers."""

from scrapers.base import BaseScraper
from scrapers.france_travail import FranceTravailScraper
from scrapers.indeed import IndeedScraper
from scrapers.ouest_france_emploi import OuestFranceEmploiScraper
from scrapers.students_jobs import StudentsJobsScraper

__all__ = [
    "BaseScraper",
    "FranceTravailScraper",
    "IndeedScraper",
    "OuestFranceEmploiScraper",
    "StudentsJobsScraper",
]
