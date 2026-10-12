"""
RawJobPosting — data collected by scrapers BEFORE AI extraction.

The scraper only knows what is visible in HTML. Fields may be None if a
website uses a different layout or hides information in JavaScript.
The LLM can still infer some missing fields from raw_text later.
"""

from pydantic import BaseModel


class RawJobPosting(BaseModel):
    url: str
    title: str | None
    company: str | None
    location: str | None
    raw_text: str
    source: str
    metadata: dict[str, object] = {}
