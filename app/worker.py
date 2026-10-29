"""ARQ worker configuration.

Run with:
    arq app.worker.WorkerSettings
"""

import logging

from arq.connections import RedisSettings

from app.config import ARQ_MAX_TRIES, JOB_TIMEOUT_SECONDS, LLM_MAX_CONCURRENT, REDIS_SETTINGS
from app.db.session import close_db, init_db
from app.observability.langsmith import configure_langsmith
from app.tasks.extraction_tasks import process_job

configure_langsmith()

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(name)s | %(message)s")


async def startup(ctx: dict) -> None:
    await init_db()


async def shutdown(ctx: dict) -> None:
    await close_db()


class WorkerSettings:
    """Settings used by the ARQ command-line worker."""

    functions = [process_job]
    redis_settings: RedisSettings = REDIS_SETTINGS
    on_startup = startup
    on_shutdown = shutdown
    max_jobs = LLM_MAX_CONCURRENT
    job_timeout = JOB_TIMEOUT_SECONDS
    max_tries = ARQ_MAX_TRIES