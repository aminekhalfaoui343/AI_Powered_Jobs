"""Async SQLModel engine shared by the API and the ARQ worker."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from app.config import DATABASE_URL
from app.db.models import ExtractedJob  # noqa: F401  — register table on SQLModel.metadata

logger = logging.getLogger(__name__)

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def is_initialized() -> bool:
    return _session_factory is not None


def _engine_kwargs(url: str) -> dict:
    kwargs: dict = {"echo": False, "pool_pre_ping": True}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
        if ":memory:" in url:
            kwargs["poolclass"] = StaticPool
    return kwargs


async def init_db(url: str | None = None) -> None:
    """Create the engine, open a connection, and ensure tables exist."""
    global _engine, _session_factory
    if _session_factory is not None:
        return

    database_url = url or DATABASE_URL
    _engine = create_async_engine(database_url, **_engine_kwargs(database_url))
    _session_factory = async_sessionmaker(
        _engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    try:
        async with _engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
        logger.info("Connected to the database")
    except Exception:
        await close_db()
        raise


async def close_db() -> None:
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _session_factory = None


async def ping_db() -> None:
    if _engine is None:
        raise RuntimeError("Database is not initialized")
    async with _engine.connect() as connection:
        await connection.exec_driver_sql("SELECT 1")


@asynccontextmanager
async def session_scope() -> AsyncIterator[AsyncSession]:
    if _session_factory is None:
        raise RuntimeError("Database is not initialized")
    async with _session_factory() as session:
        yield session
