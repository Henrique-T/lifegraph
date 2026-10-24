"""Produce auditable Checkpoint B.1 coverage and selection artifacts."""

from __future__ import annotations

import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
POSITIVE_CRITICAL = (
    "reordered", "possessive", "apposition", "reported", "uncertain",
    "negated", "coordination", "pronoun", "partial_endpoint", "distractor_heavy",
)


def read(name: str) -> object:
    """Read one UTF-8 experiment artifact."""
    return json.loads((HERE / name).read_text(encoding="utf-8"))


def matched_pairs(expected: list[dict], predicted: list[dict]) -> list[tuple[int, int]]:
    """Match by frozen canonical type and exact relation surface."""
    used: set[int] = set()
    pairs = []
    for expected_index, oracle in enumerate(expected):
        options = [
            index for index, item in enumerate(predicted)
            if index not in used and item["relation_type"] == oracle["relation_type"]
            and item["relation_surface_text"].casefold() == oracle["relation_surface_text"].casefold()
        ]
        if options:
            used.add(options[0])
            pairs.append((expected_index, options[0]))
    return pairs


def safety_cases(rows: list[dict]) -> list[dict]:
    """Identify concrete candidates contributing to the unsafe-persistible metric."""
    failures = []
    for row in rows:
        expected = row["case"]["expected_relation_candidates"]
        predicted = row["result"]["candidates"]
        pairs = matched_pairs(expected, predicted)
        used = {predicted_index for _, predicted_index in pairs}
        for expected_index, predicted_index in pairs:
            oracle = expected[expected_index]
            item = predicted[predicted_index]
            a_match = (item["endpoint_a_mention"] or "").casefold() == (oracle["endpoint_a_mention"] or "").casefold()
            b_match = (item["endpoint_b_mention"] or "").casefold() == (oracle["endpoint_b_mention"] or "").casefold()
            if item["persistence_eligibility"] == "LINGUISTICALLY_ELIGIBLE_REVIEW_AND_BINDING_REQUIRED" and (not oracle["persistible_in_v1"] or not a_match or not b_match):
                failures.append({"case_id": row["case"]["case_id"], "reason": "matched prediction incorrectly eligible", "oracle": oracle, "prediction": item})
        for index, item in enumerate(predicted):
            if index not in used and item["persistence_eligibility"] == "LINGUISTICALLY_ELIGIBLE_REVIEW_AND_BINDING_REQUIRED":
                failures.append({"case_id": row["case"]["case_id"], "reason": "extra eligible candidate", "prediction": item})
    return failures


def gate_result(metrics: dict, policy: str) -> bool:
    """Apply one candidate coverage policy independently of strategy identity."""
    end = metrics["end_to_end"]
    coverage = metrics["coverage"]
    type_floor = min(coverage["per_relation_type_recall"].values())
    available = [coverage["per_phenomenon_recall"].get(tag, 0.0) for tag in POSITIVE_CRITICAL]
    phenomenon_floor = min(available)
    if policy == "R1":
        return end["recall"] >= 0.50
    if policy == "R2":
        return coverage["persistible_oracle_recall"] >= 0.50
    if policy == "R3":
        return coverage["persistible_oracle_recall"] >= 0.50 and type_floor >= 0.30
    if policy == "R4":
        return coverage["persistible_oracle_recall"] >= 0.50 and type_floor >= 0.30 and phenomenon_floor >= 0.20
    raise ValueError(policy)


def main() -> None:
    """Write the policy matrix, failure cases, and final non-promotion decision."""
    selected = read("metrics.json")
    rows = {key: read(f"predictions_{key}.json") for key in selected}
    safety = {
        key: {
            "wrong_resolved_endpoint": value["metrics"]["end_to_end"]["wrong_resolved_endpoint"],
            "unsafe_persistible_false_positive": value["metrics"]["end_to_end"]["unsafe_persistible_false_positive"],
            "case_details": safety_cases(rows[key]),
        }
        for key, value in selected.items()
    }
    policies = {
        "R1": {"conditions": "global end-to-end recall >= 0.50"},
        "R2": {"conditions": "persistible-oracle recall >= 0.50"},
        "R3": {"conditions": "persistible-oracle recall >= 0.50 and every relation type >= 0.30"},
        "R4": {"conditions": "R3 plus every positive critical phenomenon family >= 0.20"},
    }
    for policy, value in policies.items():
        value["passes"] = {key: gate_result(item["metrics"], policy) for key, item in selected.items()}
    strategy_selection = {
        "historical_context": "B_SELECTED_BY_ORIGINAL_CHECKPOINT_B_ORDER",
        "recommended_coverage_policy": "R4",
        "coverage_policy_basis": {
            "global": "At least half of safely persistible development claims must be recovered.",
            "relation_floor": "No approved relation type may have less than 30% correct recovery.",
            "phenomenon_floor": "No positive critical stress family may be entirely ignored; a 20% lower bound is intentionally minimal.",
        },
        "safety_gate_pass": {
            key: value["wrong_resolved_endpoint"] == 0 and value["unsafe_persistible_false_positive"] == 0
            for key, value in safety.items()
        },
        "coverage_gate_pass": policies["R4"]["passes"],
        "production_selection": "NO_STRATEGY_PASSES_COVERAGE_GATE",
        "integrated": False,
    }
    per_phenomenon = {
        key: value["metrics"]["coverage"]["per_phenomenon_recall"]
        for key, value in selected.items()
    }
    for name, value in (
        ("safety_failures.json", safety),
        ("coverage_gate_policies.json", policies),
        ("strategy_selection.json", strategy_selection),
        ("per_phenomenon_metrics.json", per_phenomenon),
    ):
        (HERE / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
