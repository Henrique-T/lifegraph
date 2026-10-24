"""Integrity and oracle tests for the separate B.1 generalization corpus."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


CORPUS = Path(__file__).resolve().parents[1] / "checkpoint_b1_generalization.jsonl"
RELATION_TYPES = {"FATHER_OF", "MOTHER_OF", "SON_OF", "DAUGHTER_OF", "BROTHER_OF", "SISTER_OF", "SPOUSE_OF"}


def cases() -> list[dict]:
    """Load strict UTF-8 B.1 cases."""
    return [json.loads(line) for line in CORPUS.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_size_ids_and_balanced_types() -> None:
    """Freeze the meaningful expansion size and relation balance."""
    values = cases()
    rows = [candidate for case in values for candidate in case["expected_relation_candidates"]]
    assert len(values) == 133
    assert [case["case_id"] for case in values] == [f"PR-{index:03d}" for index in range(181, 314)]
    assert len(rows) == 119
    assert Counter(row["relation_type"] for row in rows) == Counter({key: 17 for key in RELATION_TYPES})


def test_surfaces_are_grounded_and_persistence_is_conservative() -> None:
    """Require exact surface evidence and the frozen linguistic gate."""
    for case in cases():
        for item in case["expected_relation_candidates"]:
            assert item["relation_surface_text"].casefold() in case["narrative"].casefold(), case["case_id"]
            allowed = (
                item["polarity"] == "POSITIVE" and item["epistemic_status"] == "ASSERTED"
                and item["reporting_mode"] == "DIRECT" and item["temporal_scope"] == "CURRENT_OR_UNSPECIFIED"
                and item["endpoint_a_mention"] is not None and item["endpoint_b_mention"] is not None
                and "partial_endpoint" not in case["tags"] and "pronoun" not in case["tags"]
            )
            assert item["persistible_in_v1"] is allowed, case["case_id"]


def test_generalization_and_negative_families_are_present() -> None:
    """Require syntactic novelty and safety-critical negative controls."""
    tags = Counter(tag for case in cases() for tag in case["tags"])
    required = {
        "reordered", "possessive", "existential_have", "apposition", "contracted_preposition",
        "discontinuous", "coordination", "appositive_chain", "reported", "negated", "uncertain",
        "question", "quoted_language", "incidental_kinship", "metaphor", "distractor_heavy",
        "pronoun", "partial_endpoint", "past", "event_only",
    }
    assert required <= tags.keys()
    assert sum(not case["expected_relation_candidates"] for case in cases()) == 28


def test_no_graph_identity_ref_or_event_derived_relation() -> None:
    """Preserve the linguistic-only and non-REF boundaries."""
    serialized = CORPUS.read_text(encoding="utf-8").casefold()
    assert "person_id" not in serialized and "refevent" not in serialized and "ref_event" not in serialized
    assert all(not case["expected_relation_candidates"] for case in cases() if "event_only" in case["tags"])
