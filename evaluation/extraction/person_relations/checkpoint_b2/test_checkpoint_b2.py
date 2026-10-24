"""Reproducibility and selection tests for Checkpoint B.2 artifacts."""

from __future__ import annotations

import json
from pathlib import Path


HERE = Path(__file__).resolve().parent


def load(name: str):
    """Read one JSON artifact."""
    return json.loads((HERE / name).read_text(encoding="utf-8"))


def test_split_is_disjoint_complete_and_development_only() -> None:
    """Require a complete 228/85 split without final-protocol references."""
    tuning, challenge = load("tuning_cases.json"), load("challenge_cases.json")
    tuning_ids = {case["case_id"] for case in tuning}
    challenge_ids = {case["case_id"] for case in challenge}
    assert (len(tuning), len(challenge)) == (228, 85)
    assert not tuning_ids & challenge_ids
    assert tuning_ids | challenge_ids == {f"PR-{index:03d}" for index in range(1, 314)}
    assert "final_protocol" not in (HERE / "split_config.json").read_text(encoding="utf-8")


def test_every_relation_type_occurs_in_both_splits() -> None:
    """Prevent a relation type from disappearing from challenge evaluation."""
    required = {"FATHER_OF", "MOTHER_OF", "SON_OF", "DAUGHTER_OF", "BROTHER_OF", "SISTER_OF", "SPOUSE_OF"}
    for name in ("tuning_cases.json", "challenge_cases.json"):
        actual = {candidate["relation_type"] for case in load(name) for candidate in case["expected_relation_candidates"]}
        assert actual == required


def test_critical_generalization_families_are_in_both_splits() -> None:
    """Require tuning/challenge evidence for each B.2 structural family."""
    required = {"reordered", "apposition", "contracted_preposition", "existential_have", "discontinuous", "coordination"}
    for name in ("tuning_cases.json", "challenge_cases.json"):
        tags = {tag for case in load(name) for tag in case["tags"]}
        assert required <= tags


def test_a0_b2_passes_safety_and_r4_on_all_splits() -> None:
    """Freeze the B.2 selection prerequisite rather than only combined metrics."""
    result = load("metrics_all.json")["A0_B2"]
    for split in ("tuning", "challenge", "combined"):
        assert result[split]["safety_pass"] is True
        assert result[split]["r4"]["overall"] is True


def test_gliner_configurations_do_not_silently_pass_coverage() -> None:
    """Keep low-coverage B/C/D1 configurations from being promoted by abstention."""
    result = load("metrics_all.json")
    for strategy in ("B_B2", "C_B2", "D1"):
        assert result[strategy]["combined"]["r4"]["overall"] is False


def test_selection_preserves_history_and_does_not_claim_integration() -> None:
    """Keep historical decisions separate from the B.2 recommendation."""
    selection = load("strategy_selection.json")
    assert selection["historical_checkpoint_b"] == "B_SELECTED_BY_ORIGINAL_CHECKPOINT_B_ORDER"
    assert selection["checkpoint_b1"] == "NO_STRATEGY_PASSES_COVERAGE_GATE"
    assert selection["checkpoint_b2"] == "A0_B2"
    assert selection["integration_performed"] is False
