"""Small configuration module shared by the API and ARQ worker."""

import os

from urllib.parse import quote_plus

from arq.connections import RedisSettings
from dotenv import load_dotenv


load_dotenv()


REDIS_DSN = os.getenv("REDIS_DSN", "redis://localhost:6379")
REDIS_SETTINGS = RedisSettings.from_dsn(REDIS_DSN)


def _database_url() -> str:
    explicit = os.getenv("DATABASE_URL", "").strip()
    if explicit:
        return explicit
    user = quote_plus(os.getenv("POSTGRES_USER", "jobintel"))
    password = quote_plus(os.getenv("POSTGRES_PASSWORD", "jobintel"))
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    name = os.getenv("POSTGRES_DB", "jobintel")
    return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{name}"


DATABASE_URL = _database_url()

# Reliability settings for LLM extraction jobs.
# Keep the ARQ worker concurrency in sync with the LLM concurrency limit.
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "liquid/lfm-2.5-2.6b:free")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

LLM_MAX_TRIES = int(os.getenv("LLM_MAX_TRIES", "2"))
LLM_JOB_TIMEOUT = int(os.getenv("LLM_JOB_TIMEOUT", "60"))
LLM_MAX_CONCURRENT = int(os.getenv("LLM_MAX_CONCURRENT", "1"))
LLM_INPUT_MAX_CHARS = int(os.getenv("LLM_INPUT_MAX_CHARS", "12000"))
SCRAPE_TIMEOUT_SECONDS = int(os.getenv("SCRAPE_TIMEOUT_SECONDS", "25"))
ARQ_MAX_TRIES = int(os.getenv("ARQ_MAX_TRIES", "2"))
OPENROUTER_LOCK_TIMEOUT = int(os.getenv("OPENROUTER_LOCK_TIMEOUT", "90"))
OPENROUTER_LOCK_BLOCKING_TIMEOUT = float(os.getenv("OPENROUTER_LOCK_BLOCKING_TIMEOUT", "0.5"))
MAX_JOBS = LLM_MAX_CONCURRENT
_DEFAULT_JOB_TIMEOUT = SCRAPE_TIMEOUT_SECONDS + (LLM_JOB_TIMEOUT * LLM_MAX_TRIES) + 30
JOB_TIMEOUT_SECONDS = int(os.getenv("ARQ_JOB_TIMEOUT", str(_DEFAULT_JOB_TIMEOUT)))

ENABLED_JOB_SOURCES = frozenset(
	source.strip().lower()
	for source in os.getenv("JOB_SOURCES_ENABLED", "france_travail").split(",")
	if source.strip()
)

# Local test/dev flags for failure simulation.
SIMULATE_LLM_TIMEOUT = os.getenv("SIMULATE_LLM_TIMEOUT", "false").lower() == "true"
SIMULATE_LLM_FAILURE = os.getenv("SIMULATE_LLM_FAILURE", "false").lower() == "true"
SIMULATE_LLM_FAILURE_COUNT = int(os.getenv("SIMULATE_LLM_FAILURE_COUNT", "2"))
SIMULATE_INVALID_LLM_RESPONSE = os.getenv("SIMULATE_INVALID_LLM_RESPONSE", "false").lower() == "true"

LANGSMITH_TRACING = os.getenv("LANGSMITH_TRACING", "false").lower() == "true"
LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY", "")
LANGSMITH_PROJECT = os.getenv("LANGSMITH_PROJECT", "job-intelligence")
LANGSMITH_WORKSPACE_ID = os.getenv("LANGSMITH_WORKSPACE_ID", "")
LANGSMITH_ENDPOINT = os.getenv("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com")


def apply_langsmith_env() -> None:
    """Expose LangSmith settings the way the official SDK expects."""
    if LANGSMITH_TRACING and LANGSMITH_API_KEY:
        os.environ["LANGSMITH_TRACING"] = "true"
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGSMITH_API_KEY"] = LANGSMITH_API_KEY
        os.environ["LANGCHAIN_API_KEY"] = LANGSMITH_API_KEY
        os.environ["LANGSMITH_PROJECT"] = LANGSMITH_PROJECT
        os.environ["LANGCHAIN_PROJECT"] = LANGSMITH_PROJECT
        os.environ["LANGSMITH_ENDPOINT"] = LANGSMITH_ENDPOINT
        if LANGSMITH_WORKSPACE_ID:
            os.environ["LANGSMITH_WORKSPACE_ID"] = LANGSMITH_WORKSPACE_ID
    else:
        os.environ.setdefault("LANGSMITH_TRACING", "false")


apply_langsmith_env()
