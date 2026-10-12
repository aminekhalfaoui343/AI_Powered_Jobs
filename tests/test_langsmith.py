from app.observability.langsmith import is_langsmith_enabled, wrap_openai_client
from app.services.extractor import try_structured_extraction
from evaluation.dataset import EXAMPLES
from evaluation.evaluators import (
    extraction_path_recorded,
    field_accuracy,
    schema_completeness,
    skills_present,
)
from models.raw_job import RawJobPosting


def test_langsmith_is_disabled_without_key(monkeypatch):
    monkeypatch.setattr("app.observability.langsmith.LANGSMITH_TRACING", True)
    monkeypatch.setattr("app.observability.langsmith.LANGSMITH_API_KEY", "")
    assert is_langsmith_enabled() is False


def test_wrap_openai_is_noop_when_disabled():
    sentinel = object()
    assert wrap_openai_client(sentinel) is sentinel


def test_schema_completeness_scores_required_fields():
    complete = schema_completeness(
        {"title": "Dev", "company": "Acme", "location": "Paris", "description": "Build APIs."}
    )
    incomplete = schema_completeness({"title": "Dev", "company": "", "location": None, "description": "Build APIs."})

    assert complete["score"] == 1.0
    assert incomplete["score"] == 0.5


def test_field_accuracy_matches_reference_company_and_title():
    result = field_accuracy(
        {"title": "Platform Engineer Junior (H/F)", "company": "EKIMETRICS FRANCE", "location": "PARIS (75)"},
        reference_outputs={"title": "Platform Engineer Junior", "company": "EKIMETRICS FRANCE", "location": "PARIS (75)"},
    )
    assert result["score"] == 1.0


def test_structured_dataset_example_passes_heuristics():
    example = EXAMPLES[0]
    raw = RawJobPosting.model_validate(example["inputs"]["raw_job"])
    job = try_structured_extraction(raw)
    assert job is not None
    outputs = job.model_dump(mode="json")

    assert schema_completeness(outputs)["score"] == 1.0
    assert skills_present(outputs)["score"] == 1.0
    assert extraction_path_recorded(outputs)["score"] == 1.0
    assert field_accuracy(outputs, reference_outputs=example["outputs"])["score"] == 1.0
