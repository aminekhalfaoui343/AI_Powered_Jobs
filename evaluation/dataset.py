"""Labeled examples used to evaluate extraction quality in LangSmith."""

from __future__ import annotations

DATASET_NAME = "job-extraction-eval"
DATASET_DESCRIPTION = "Labeled job postings used to evaluate structured and LLM extraction."

EXAMPLES: list[dict] = [
    {
        "inputs": {
            "path": "structured",
            "raw_job": {
                "url": "https://candidat.francetravail.fr/offres/recherche/detail/214JPDD",
                "title": "Platform Engineer Junior",
                "company": "EKIMETRICS FRANCE",
                "location": "PARIS (75)",
                "raw_text": "Title: Platform Engineer Junior\nCompany: EKIMETRICS FRANCE\nDescription: Build platform tooling.",
                "source": "France Travail",
                "metadata": {
                    "structured": True,
                    "extraction_path": "france_travail_bff",
                    "description": "Build platform tooling for Data and AI products.",
                    "skills": ["Kubernetes", "Terraform"],
                    "contract_type": "CDI",
                    "salary": "42000 Euros",
                },
            },
        },
        "outputs": {
            "title": "Platform Engineer Junior",
            "company": "EKIMETRICS FRANCE",
            "location": "PARIS (75)",
        },
    },
    {
        "inputs": {
            "path": "llm",
            "raw_job": {
                "url": "https://example.com/jobs/python-dev",
                "title": "Python Developer",
                "company": "Example Corp",
                "location": "Paris",
                "raw_text": (
                    "Example Corp is hiring a Python Developer in Paris. "
                    "You will build backend services with FastAPI and PostgreSQL. "
                    "Contract: CDI. Experience: 2+ years."
                ),
                "source": "example",
                "metadata": {},
            },
        },
        "outputs": {
            "title": "Python Developer",
            "company": "Example Corp",
            "location": "Paris",
        },
    },
]
