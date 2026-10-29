from __future__ import annotations

from urllib.parse import urlparse

from pydantic import BaseModel, model_validator


class DiscoveredJob(BaseModel):
    """Normalized result returned by a discovery adapter for one job listing."""

    title: str | None = None
    company: str | None = None
    location: str | None = None
    description: str | None = None
    url: str
    source: str
    sources: list[str] = []
    metadata: dict[str, object] = {}

    @model_validator(mode="after")
    def validate_url_and_source(self) -> "DiscoveredJob":
        parsed = urlparse(self.url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("url must be a valid HTTP or HTTPS URL")
        if not self.source or not self.source.strip():
            raise ValueError("source is required")
        if not self.sources:
            self.sources = [self.source]
        return self
