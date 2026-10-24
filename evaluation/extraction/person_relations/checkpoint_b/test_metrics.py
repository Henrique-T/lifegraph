"""Regression tests for Checkpoint B safety metrics."""

from copy import deepcopy

from run import score


def oracle_case() -> dict:
    """Return one minimal persistible oracle case."""

    return {
        "case_id": "METRIC-1",
        "narrative": "João é pai de Maria.",
        "tags": ["direct"],
        "expected_relation_candidates": [{
            "relation_type": "FATHER_OF",
            "relation_surface_text": "pai de",
            "endpoint_a_mention": "João",
            "endpoint_b_mention": "Maria",
            "polarity": "POSITIVE",
            "epistemic_status": "ASSERTED",
            "reporting_mode": "DIRECT",
            "temporal_scope": "CURRENT_OR_UNSPECIFIED",
            "persistible_in_v1": True,
        }],
    }


def predicted_candidate() -> dict:
    """Return the matching candidate representation needed by metrics."""

    return {
        "relation_type": "FATHER_OF",
        "relation_surface_text": "pai de",
        "endpoint_a_mention": "João",
        "endpoint_b_mention": "Maria",
        "endpoint_a_resolution_state": "RESOLVED_MENTION",
        "endpoint_b_resolution_state": "RESOLVED_MENTION",
        "polarity": "POSITIVE",
        "epistemic_status": "ASSERTED",
        "reporting_mode": "DIRECT",
        "reporting_source_mention": None,
        "temporal_scope": "CURRENT_OR_UNSPECIFIED",
        "persistence_eligibility": "LINGUISTICALLY_ELIGIBLE_REVIEW_AND_BINDING_REQUIRED",
    }


def result_row(case: dict, candidate: dict) -> dict:
    """Wrap one case and prediction for the pure scorer."""

    start = case["narrative"].index("pai de")
    return {
        "case": case,
        "result": {
            "detections": [{"start": start, "end": start + 6, "text": "pai de"}],
            "candidates": [candidate],
        },
    }


def test_wrong_resolved_endpoint_is_a_hard_safety_count() -> None:
    """Count a specific incorrect resolved mention and unsafe eligibility."""

    item = predicted_candidate()
    item["endpoint_a_mention"] = "Pedro"
    metrics = score([result_row(oracle_case(), item)])
    assert metrics["end_to_end"]["wrong_resolved_endpoint"] == 1
    assert metrics["end_to_end"]["unsafe_persistible_false_positive"] == 1


def test_safe_unresolved_endpoint_is_not_wrong_resolution() -> None:
    """Separate conservative abstention from wrong resolved endpoint."""

    case = oracle_case()
    case["tags"] = ["partial_endpoint", "pronoun"]
    case["expected_relation_candidates"][0]["endpoint_a_mention"] = "Ele"
    case["expected_relation_candidates"][0]["persistible_in_v1"] = False
    case["narrative"] = "Ele é pai de Maria."
    item = predicted_candidate()
    item["endpoint_a_mention"] = "Ele"
    item["endpoint_a_resolution_state"] = "UNRESOLVED_MENTION"
    item["persistence_eligibility"] = "NOT_PERSISTIBLE_PARTIAL_ENDPOINT"
    metrics = score([result_row(case, item)])
    assert metrics["end_to_end"]["wrong_resolved_endpoint"] == 0
    assert metrics["end_to_end"]["safe_abstentions"] == 1


def test_false_candidate_that_looks_persistible_is_unsafe() -> None:
    """Count factualization in a no-relation case as the hard safety metric."""

    case = oracle_case()
    case["expected_relation_candidates"] = []
    case["tags"] = ["incidental_kinship", "no_relation"]
    metrics = score([result_row(case, deepcopy(predicted_candidate()))])
    assert metrics["end_to_end"]["unsafe_persistible_false_positive"] == 1
    assert metrics["failure_taxonomy"]["INCIDENTAL_KINSHIP_FACTUALIZED"] == 1
