from __future__ import annotations

from pydantic import BaseModel, Field, field_validator, model_validator


class JobSearchRequest(BaseModel):
    """Request payload for a multi-job discovery/search workflow."""

    query: str
    location: str | None = None
    sources: list[str] | None = None
    max_results_per_source: int = Field(default=20, ge=1, le=100)

    @field_validator("query")
    @classmethod
    def validate_query(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("query cannot be blank")
        return cleaned

    @field_validator("sources", mode="before")
    @classmethod
    def normalize_sources(cls, value):
        if value is None:
            return None
        if isinstance(value, str):
            value = [value]
        normalized = []
        for item in value:
            if item is None:
                continue
            cleaned = str(item).strip().lower()
            if cleaned:
                normalized.append(cleaned)
        return normalized

    @model_validator(mode="after")
    def validate_location_and_sources(self) -> "JobSearchRequest":
        if self.location is not None:
            self.location = self.location.strip() or None
        return self
