"""Regression tests proving that B.1 safety and coverage metrics resist silence."""

from __future__ import annotations

import sys
from types import SimpleNamespace

# Metric tests do not load a model; this keeps the pure evaluator independently testable.
sys.modules.setdefault("gliner2", SimpleNamespace(AutoExtractor=object))

import run  # noqa: E402


def oracle(*, partial: bool = False, persistible: bool = True) -> dict:
    """Return one minimal development oracle candidate."""
    return {
        "relation_type": "FATHER_OF", "relation_surface_text": "pai de",
        "endpoint_a_mention": None if partial else "João", "endpoint_b_mention": "Maria",
        "polarity": "POSITIVE", "epistemic_status": "ASSERTED", "reporting_mode": "DIRECT",
        "temporal_scope": "CURRENT_OR_UNSPECIFIED", "persistible_in_v1": persistible,
        "rationale": "metric fixture",
    }


def prediction(*, endpoint_a: str | None = "João", eligible: bool = True) -> dict:
    """Return one minimal candidate-shaped metric fixture."""
    return {
        "relation_type": "FATHER_OF", "relation_surface_text": "pai de",
        "endpoint_a_mention": endpoint_a, "endpoint_b_mention": "Maria",
        "endpoint_a_resolution_state": "UNRESOLVED_MENTION" if endpoint_a is None else "RESOLVED_MENTION",
        "endpoint_b_resolution_state": "RESOLVED_MENTION", "polarity": "POSITIVE",
        "epistemic_status": "ASSERTED", "reporting_mode": "DIRECT", "temporal_scope": "CURRENT_OR_UNSPECIFIED",
        "reporting_source_mention": None,
        "persistence_eligibility": "LINGUISTICALLY_ELIGIBLE_REVIEW_AND_BINDING_REQUIRED" if eligible else "NOT_PERSISTIBLE_PARTIAL_ENDPOINT",
    }


def row(expected: dict, predicted: list[dict], *, tags: list[str] | None = None) -> dict:
    """Wrap fixtures in the evaluator row format."""
    return {
        "case": {"case_id": "FIXTURE", "narrative": "João é pai de Maria.",
                 "expected_relation_candidates": [expected], "tags": tags or ["direct"]},
        "result": {"detections": [], "candidates": predicted},
    }


def test_correct_candidate_and_total_miss_are_distinct() -> None:
    """Silence must have zero coverage even though it has no unsafe resolution."""
    correct = run.b1_metrics([row(oracle(), [prediction()])])
    silence = run.b1_metrics([row(oracle(), [])])
    assert correct["coverage"]["persistible_oracle_recall"] == 1.0
    assert silence["coverage"]["persistible_oracle_recall"] == 0.0
    assert silence["coverage"]["total_detector_candidate_miss"] == 1
    assert silence["end_to_end"]["wrong_resolved_endpoint"] == 0


def test_wrong_endpoint_and_unsafe_persistible_are_counted() -> None:
    """A wrong concrete endpoint must trigger both applicable safety metrics."""
    metrics = run.b1_metrics([row(oracle(), [prediction(endpoint_a="Pedro")])])
    assert metrics["end_to_end"]["wrong_resolved_endpoint"] == 1
    assert metrics["end_to_end"]["unsafe_persistible_false_positive"] == 1


def test_unsafe_candidate_for_nonpersistible_oracle_is_counted() -> None:
    """A linguistically eligible prediction cannot factualize a blocked oracle."""
    expected = oracle(persistible=False)
    expected["polarity"] = "NEGATED"
    metrics = run.b1_metrics([row(expected, [prediction()])])
    assert metrics["end_to_end"]["unsafe_persistible_false_positive"] == 1


def test_safe_and_unnecessary_abstention_are_separate() -> None:
    """Approved partial abstention and avoidable abstention use separate denominators."""
    safe = run.b1_metrics([row(oracle(partial=True, persistible=False), [prediction(endpoint_a=None, eligible=False)], tags=["partial_endpoint"])])
    unnecessary = run.b1_metrics([row(oracle(), [prediction(endpoint_a=None, eligible=False)])])
    assert safe["coverage"]["safe_abstention_count"] == 1
    assert safe["coverage"]["safe_abstention_rate"] == 1.0
    assert unnecessary["coverage"]["unnecessary_abstention_count"] == 1
    assert unnecessary["coverage"]["unnecessary_abstention_rate"] == 1.0
