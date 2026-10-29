"""
JobPosting — normalized job data after structured LLM extraction.

Every website eventually maps to this same schema so the rest of the
platform (search, analytics, storage) can treat all sources uniformly.
"""

from pydantic import BaseModel, Field


class JobPosting(BaseModel):
    title: str
    company: str
    location: str
    description: str
    skills: list[str] = Field(default_factory=list)
    experience: str | None = None
    education: str | None = None
    salary: str | None = None
    contract_type: str | None = None
    source: str | None = None
    source_url: str | None = None
    sources: list[str] = Field(default_factory=list)
    remote: bool | None = None
    remote_type: str | None = None
    posted_date: str | None = None
    application_deadline: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)
