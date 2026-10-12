"""SQLModel tables for durable extracted-job storage."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Column, DateTime, JSON, Text
from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ExtractedJob(SQLModel, table=True):
    """One ARQ job's extraction result, kept after Redis forgets the pickle."""

    __tablename__ = "extracted_jobs"

    job_id: str = Field(primary_key=True, max_length=64)
    status: str = Field(index=True, max_length=32)
    url: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    title: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    company: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    location: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    source: str | None = Field(default=None, max_length=128)
    skills: list[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    result: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    error: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    created_at: datetime = Field(
        default_factory=_utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=_utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
