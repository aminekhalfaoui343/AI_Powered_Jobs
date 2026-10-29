"""Run a LangSmith evaluation experiment against the job extractor.

Usage:
    python -m evaluation.run

Requires LANGSMITH_TRACING=true and LANGSMITH_API_KEY.
France Travail structured examples never call the LLM.
The LLM example only runs if OPENROUTER_API_KEY is set.
"""

from __future__ import annotations

import logging

from app.config import LANGSMITH_PROJECT, OPENROUTER_API_KEY, apply_langsmith_env
from app.observability.langsmith import configure_langsmith, is_langsmith_enabled
from app.services.extractor import try_structured_extraction
from evaluation.dataset import DATASET_DESCRIPTION, DATASET_NAME, EXAMPLES
from evaluation.evaluators import EVALUATORS
from extraction.openrouter_extractor import extract_job_posting
from models.raw_job import RawJobPosting

logger = logging.getLogger(__name__)


def extract_target(inputs: dict) -> dict:
    raw = RawJobPosting.model_validate(inputs["raw_job"])
    path = inputs.get("path") or "llm"
    if path == "structured":
        job = try_structured_extraction(raw)
        if job is None:
            return {"error": "structured extraction returned None"}
        return job.model_dump(mode="json")
    if not OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY is required to evaluate the LLM extraction path")
    job = extract_job_posting(raw)
    return job.model_dump(mode="json")


def ensure_dataset(client) -> str:
    existing = list(client.list_datasets(dataset_name=DATASET_NAME))
    if existing:
        dataset = existing[0]
        logger.info("Using existing LangSmith dataset id=%s", dataset.id)
        return dataset.id

    dataset = client.create_dataset(DATASET_NAME, description=DATASET_DESCRIPTION)
    client.create_examples(
        dataset_id=dataset.id,
        examples=[
            {"inputs": example["inputs"], "outputs": example["outputs"]}
            for example in EXAMPLES
        ],
    )
    logger.info("Created LangSmith dataset id=%s examples=%s", dataset.id, len(EXAMPLES))
    return dataset.id


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
    apply_langsmith_env()
    configure_langsmith()
    if not is_langsmith_enabled():
        raise SystemExit(
            "LangSmith is disabled. Set LANGSMITH_TRACING=true and LANGSMITH_API_KEY, then retry."
        )

    from langsmith import Client, evaluate

    client = Client()
    dataset_id = ensure_dataset(client)
    results = evaluate(
        extract_target,
        data=DATASET_NAME,
        evaluators=EVALUATORS,
        experiment_prefix="job-extraction",
        metadata={"project": LANGSMITH_PROJECT, "dataset_id": dataset_id},
        max_concurrency=2,
    )
    print(results)
    print("Open the experiment in LangSmith to compare scores and traces.")


if __name__ == "__main__":
    main()
