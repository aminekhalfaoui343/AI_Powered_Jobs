"""Heuristic evaluators for job extraction. These do not call an LLM."""

from __future__ import annotations

from typing import Any


REQUIRED_FIELDS = ("title", "company", "location", "description")


def _outputs(payload: dict[str, Any]) -> dict[str, Any]:
    return payload.get("outputs") or payload


def schema_completeness(outputs: dict[str, Any], **_: Any) -> dict[str, Any]:
    """Score 1.0 when title, company, location, and description are present."""
    data = _outputs(outputs)
    present = sum(1 for field in REQUIRED_FIELDS if str(data.get(field) or "").strip())
    score = present / len(REQUIRED_FIELDS)
    return {
        "key": "schema_completeness",
        "score": score,
        "comment": f"{present}/{len(REQUIRED_FIELDS)} required fields present",
    }


def skills_present(outputs: dict[str, Any], **_: Any) -> dict[str, Any]:
    data = _outputs(outputs)
    skills = data.get("skills") or []
    score = 1.0 if isinstance(skills, list) and len(skills) > 0 else 0.0
    return {
        "key": "skills_present",
        "score": score,
        "comment": f"{len(skills) if isinstance(skills, list) else 0} skills extracted",
    }


def field_accuracy(
    outputs: dict[str, Any],
    reference_outputs: dict[str, Any] | None = None,
    **_: Any,
) -> dict[str, Any]:
    """Compare extracted title/company/location to labeled reference values."""
    if not reference_outputs:
        return {"key": "field_accuracy", "score": None, "comment": "No reference outputs"}

    data = _outputs(outputs)
    comparable = ("title", "company", "location")
    matches = 0
    checked = 0
    for field in comparable:
        expected = str(reference_outputs.get(field) or "").strip().lower()
        if not expected:
            continue
        checked += 1
        actual = str(data.get(field) or "").strip().lower()
        if expected in actual or actual in expected:
            matches += 1
    score = matches / checked if checked else None
    return {
        "key": "field_accuracy",
        "score": score,
        "comment": f"{matches}/{checked} labeled fields matched",
    }


def extraction_path_recorded(outputs: dict[str, Any], **_: Any) -> dict[str, Any]:
    data = _outputs(outputs)
    metadata = data.get("metadata") if isinstance(data.get("metadata"), dict) else {}
    path = metadata.get("extraction_path") or data.get("extraction_path")
    return {
        "key": "extraction_path_recorded",
        "score": 1.0 if path else 0.0,
        "comment": str(path or "missing"),
    }


EVALUATORS = [
    schema_completeness,
    skills_present,
    field_accuracy,
    extraction_path_recorded,
]
