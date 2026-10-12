"""LangSmith tracing helpers.

The SDK is optional at import time so unit tests still run if the package is
missing. Traces are sent only when LANGSMITH_TRACING=true and an API key is set.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from app.config import (
    LANGSMITH_API_KEY,
    LANGSMITH_PROJECT,
    LANGSMITH_TRACING,
    apply_langsmith_env,
)

logger = logging.getLogger(__name__)


def _identity_traceable(*args: Any, **kwargs: Any) -> Callable:
    def decorator(fn: Callable) -> Callable:
        return fn

    if args and callable(args[0]) and not kwargs:
        return args[0]
    return decorator


try:
    from langsmith import traceable as _langsmith_traceable
    from langsmith.wrappers import wrap_openai as _wrap_openai
except ImportError:  # pragma: no cover - local/test environments without the extra
    _langsmith_traceable = _identity_traceable
    _wrap_openai = None


traceable = _langsmith_traceable


def is_langsmith_enabled() -> bool:
    return bool(LANGSMITH_TRACING and LANGSMITH_API_KEY)


def configure_langsmith() -> bool:
    apply_langsmith_env()
    enabled = is_langsmith_enabled()
    if enabled:
        logger.info("LangSmith tracing enabled project=%s", LANGSMITH_PROJECT)
    else:
        logger.info("LangSmith tracing disabled")
    return enabled


def wrap_openai_client(client: Any) -> Any:
    """Wrap an OpenAI-compatible client so each completion becomes an LLM span."""
    if not is_langsmith_enabled() or _wrap_openai is None:
        return client
    return _wrap_openai(client)
