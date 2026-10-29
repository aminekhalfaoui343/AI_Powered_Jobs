"""Stage B extraction through OpenRouter's OpenAI-compatible API.

The module name is kept for compatibility with existing pipeline imports.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from typing import Any

from openai import APIConnectionError, APIStatusError, APITimeoutError, OpenAI, RateLimitError
from pydantic import BaseModel, Field, ValidationError

from app.config import (
    LLM_INPUT_MAX_CHARS,
    LLM_JOB_TIMEOUT,
    LLM_MAX_CONCURRENT as LLM_MAX_CONCURRENT_CONFIG,
    LLM_MAX_TRIES,
    OPENROUTER_API_KEY,
    OPENROUTER_BASE_URL,
    OPENROUTER_MODEL,
    SIMULATE_INVALID_LLM_RESPONSE,
    SIMULATE_LLM_FAILURE,
    SIMULATE_LLM_FAILURE_COUNT,
    SIMULATE_LLM_TIMEOUT,
)
from app.observability.langsmith import traceable, wrap_openai_client
from models.job_posting import JobPosting
from models.raw_job import RawJobPosting

logger = logging.getLogger(__name__)
LLM_MAX_CONCURRENT = LLM_MAX_CONCURRENT_CONFIG

SYSTEM_PROMPT = """You extract job postings into the exact JSON schema provided.
Return JSON only. Do not include markdown, comments, explanations, or extra keys.
Use only information present or reasonably implied in the job posting.
For missing optional fields use null; skills must be a list of strings.
description must be a concise 2-4 sentence summary of the role.
location should be city/region/country, or Remote when explicitly remote.
contract_type examples include CDI, CDD, Stage, Alternance, Intermittent, and Freelance.
"""


class LLMJobExtraction(BaseModel):
    """Strict LLM output schema. Keep this smaller than JobPosting.

    JobPosting.metadata uses additionalProperties, which OpenRouter rejects in
    strict json_schema mode and forces a slower json_object retry.
    """

    title: str
    company: str
    location: str
    description: str
    skills: list[str] = Field(default_factory=list)
    experience: str | None = None
    education: str | None = None
    salary: str | None = None
    contract_type: str | None = None
    remote: bool | None = None


class InvalidLLMResponseError(ValueError):
    """Provider output was received but was not valid JobPosting JSON."""


def _is_retryable_llm_error(exc: BaseException) -> bool:
    if isinstance(exc, (TimeoutError, ConnectionError, OSError, APIConnectionError, APITimeoutError, RateLimitError)):
        return True
    if isinstance(exc, APIStatusError):
        return exc.status_code in {408, 409, 429} or 500 <= exc.status_code < 600
    return False


def _retry_delay_for_attempt(attempt: int) -> float:
    return min(0.5 * (2 ** (attempt - 1)), 4.0)


def _simulate_failure_for_attempt(attempt: int) -> None:
    if SIMULATE_LLM_TIMEOUT:
        raise TimeoutError("Simulated LLM timeout")
    if SIMULATE_LLM_FAILURE and attempt <= SIMULATE_LLM_FAILURE_COUNT:
        raise APIConnectionError("Simulated temporary provider failure")
    if SIMULATE_INVALID_LLM_RESPONSE and attempt == 1:
        raise InvalidLLMResponseError("Simulated invalid LLM response")


def create_openrouter_client() -> OpenAI:
    if not OPENROUTER_API_KEY:
        raise ValueError("OPENROUTER_API_KEY is not set. Add it to your .env file.")
    client = OpenAI(
        api_key=OPENROUTER_API_KEY,
        base_url=OPENROUTER_BASE_URL,
        default_headers={
            "HTTP-Referer": "https://github.com/job-scraper",
            "X-Title": "Job Scraper",
        },
    )
    return wrap_openai_client(client)


def get_openrouter_model() -> str:
    return OPENROUTER_MODEL


def _build_user_message(raw_job: RawJobPosting) -> str:
    parts = []
    if raw_job.title:
        parts.append(f"Title hint: {raw_job.title}")
    if raw_job.company:
        parts.append(f"Company hint: {raw_job.company}")
    if raw_job.location:
        parts.append(f"Location hint: {raw_job.location}")
    parts.append("\n--- JOB POSTING TEXT ---\n")
    parts.append(raw_job.raw_text[:LLM_INPUT_MAX_CHARS])
    return "\n".join(parts)


def _request_completion(client: OpenAI, model: str, user_message: str, response_format: dict[str, Any]):
    return client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        response_format=response_format,
        temperature=0.1,
        timeout=LLM_JOB_TIMEOUT,
    )


def _call_llm_once(raw_job: RawJobPosting):
    if not raw_job.raw_text or len(raw_job.raw_text.strip()) < 50:
        raise ValueError("Raw job text is too short for LLM extraction")

    client = create_openrouter_client()
    model = get_openrouter_model()
    user_message = _build_user_message(raw_job)
    logger.info(
        "Sending job to OpenRouter model=%s (text_len=%d)",
        model,
        min(len(raw_job.raw_text), LLM_INPUT_MAX_CHARS),
    )

    try:
        completion = _request_completion(
            client,
            model,
            user_message,
            {
                "type": "json_schema",
                "json_schema": {
                    "name": "job_posting",
                    "strict": True,
                    "schema": LLMJobExtraction.model_json_schema(),
                },
            },
        )
    except APIStatusError as exc:
        if exc.status_code == 400:
            logger.warning("OpenRouter rejected json_schema; retrying with json_object")
            schema_hint = json.dumps(LLMJobExtraction.model_json_schema(), indent=2)
            completion = _request_completion(
                client,
                model,
                SYSTEM_PROMPT + f"\nExpected JSON schema:\n{schema_hint}\n\n{user_message}",
                {"type": "json_object"},
            )
        else:
            logger.warning("OpenRouter API error status=%s", exc.status_code)
            raise
    except APIConnectionError:
        logger.warning("Cannot connect to OpenRouter base_url=%s", OPENROUTER_BASE_URL)
        raise

    return _parse_completion_response(completion, raw_job)


def _json_content(content: str) -> str:
    content = content.strip()
    fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", content, re.DOTALL | re.IGNORECASE)
    return fenced.group(1).strip() if fenced else content


def _parse_completion_response(completion: Any, raw_job: RawJobPosting) -> JobPosting:
    content = completion.choices[0].message.content
    if not content or not content.strip():
        raise InvalidLLMResponseError("OpenRouter returned empty message content")

    try:
        output: dict[str, Any] = json.loads(_json_content(content))
    except json.JSONDecodeError as exc:
        logger.warning("OpenRouter returned malformed JSON")
        raise InvalidLLMResponseError(f"OpenRouter returned invalid JSON: {exc}") from exc

    try:
        extracted = LLMJobExtraction.model_validate(output)
    except ValidationError as exc:
        logger.warning("OpenRouter JSON failed JobPosting validation")
        raise InvalidLLMResponseError(f"Invalid LLM response payload: {exc}") from exc

    job = JobPosting(
        title=extracted.title,
        company=extracted.company,
        location=extracted.location,
        description=extracted.description,
        skills=extracted.skills,
        experience=extracted.experience,
        education=extracted.education,
        salary=extracted.salary,
        contract_type=extracted.contract_type,
        remote=extracted.remote,
        source=raw_job.source,
        source_url=raw_job.url,
        metadata={"extraction_path": "llm"},
    )

    logger.info("Structured extraction successful title=%r company=%r", job.title, job.company)
    return job


async def extract_job_posting_with_retry(raw_job: RawJobPosting) -> JobPosting:
    started_at = time.perf_counter()
    for attempt in range(1, LLM_MAX_TRIES + 1):
        logger.info("LLM extraction attempt=%s/%s job_url=%s", attempt, LLM_MAX_TRIES, raw_job.url)
        try:
            _simulate_failure_for_attempt(attempt)
            result = await asyncio.wait_for(
                asyncio.to_thread(extract_job_posting, raw_job),
                timeout=LLM_JOB_TIMEOUT,
            )
            logger.info("LLM extraction completed duration=%.2fs job_url=%s", time.perf_counter() - started_at, raw_job.url)
            return result
        except asyncio.TimeoutError as exc:
            error: BaseException = TimeoutError(f"LLM extraction timed out after {LLM_JOB_TIMEOUT} seconds")
        except InvalidLLMResponseError as exc:
            error = exc
        except Exception as exc:
            error = exc

        retryable = isinstance(error, InvalidLLMResponseError) or _is_retryable_llm_error(error)
        if not retryable or attempt >= LLM_MAX_TRIES:
            logger.error("LLM extraction failed attempt=%s/%s error=%s", attempt, LLM_MAX_TRIES, error)
            raise error
        delay = _retry_delay_for_attempt(attempt)
        logger.warning("LLM extraction failed attempt=%s/%s; retrying in %.1fs", attempt, LLM_MAX_TRIES, delay)
        await asyncio.sleep(delay)

    raise RuntimeError("LLM extraction failed without producing a result")


@traceable(name="llm_extract_job", run_type="llm", metadata={"provider": "openrouter"})
def extract_job_posting(raw_job: RawJobPosting) -> JobPosting:
    """Synchronous OpenRouter call used by the async retry wrapper."""
    return _call_llm_once(raw_job)
