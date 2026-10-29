"""Read ARQ job results without crashing on unpickleable provider exceptions."""

from __future__ import annotations

import io
import logging
import pickle
from typing import Any

from arq.constants import result_key_prefix
from arq.jobs import Job, JobStatus

logger = logging.getLogger(__name__)


class _CompatError(Exception):
    """Stand-in for provider exceptions that cannot be reconstructed by pickle."""

    def __init__(self, *args: object, **kwargs: object) -> None:
        message = args[0] if args else kwargs.get("message") or kwargs.get("body") or type(self).__name__
        super().__init__(message)
        self.args = args or (message,)
        for key, value in kwargs.items():
            setattr(self, key, value)

    def __setstate__(self, state: object) -> None:
        if isinstance(state, dict):
            self.__dict__.update(state)


class _CompatUnpickler(pickle.Unpickler):
    def find_class(self, module: str, name: str):
        try:
            cls = super().find_class(module, name)
        except Exception:
            return type(name, (_CompatError,), {})
        if module.startswith("openai") or name.endswith("Error"):
            return type(name, (_CompatError,), {})
        return cls


def safe_unpickle(raw: bytes) -> Any:
    return _CompatUnpickler(io.BytesIO(raw)).load()


def _format_error(value: object) -> str:
    if isinstance(value, BaseException):
        detail = str(value).strip()
        name = type(value).__name__
        combined = f"{name} {detail} {type(value).__module__}"
        if "APIStatusError" in combined or "openai" in type(value).__module__:
            return (
                "The LLM provider rejected this listing. Restart the ARQ worker so "
                "France Travail jobs use structured extraction instead of OpenRouter."
            )
        return f"{name}: {detail}" if detail else name
    text = str(value).strip()
    if "APIStatusError" in text or "unable to deserialize" in text.lower():
        return (
            "The LLM provider rejected this listing. Restart the ARQ worker so "
            "France Travail jobs use structured extraction instead of OpenRouter."
        )
    return text or "Extraction failed"


async def read_job_outcome(job: Job) -> dict[str, Any]:
    """Return API payload fields for a queued ARQ job without raising provider errors."""
    job_status = await job.status()
    payload: dict[str, Any] = {"job_id": job.job_id, "status": job_status.value, "result": None}
    if job_status != JobStatus.complete:
        return payload

    raw = await job._redis.get(result_key_prefix + job.job_id)
    if not raw:
        payload["status"] = "failed"
        payload["error"] = "Job finished but the result is no longer available in Redis"
        return payload

    try:
        data = safe_unpickle(raw)
    except Exception as exc:
        logger.exception("Could not unpickle job result job_id=%s", job.job_id)
        payload["status"] = "failed"
        payload["error"] = _format_error(exc)
        return payload

    success = bool(data.get("s")) if isinstance(data, dict) else False
    result = data.get("r") if isinstance(data, dict) else data

    if not success:
        payload["status"] = "failed"
        payload["error"] = _format_error(result)
        return payload

    if isinstance(result, dict) and result.get("extraction_status") == "failed":
        payload["status"] = "failed"
        payload["error"] = result.get("error") or "Extraction failed"
        payload["result"] = {
            key: value
            for key, value in result.items()
            if key not in {"extraction_status", "error"} and value is not None
        } or None
        return payload

    payload["result"] = result
    return payload
