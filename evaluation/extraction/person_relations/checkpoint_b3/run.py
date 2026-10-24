"""Evaluate the frozen A0_B3 extraction candidate without route integration."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
GLINER_APP = ROOT / "gliner-service"
B2 = HERE.parent / "checkpoint_b2"
for path in (GLINER_APP, B2):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


b2 = load_module("lifegraph_b2_run_for_b3", B2 / "run.py")
validation = load_module("lifegraph_b3_validation", HERE / "unseen_validation.py")

from app.relation_extraction_b2 import (  # noqa: E402
    A0_B2_MODEL_ID, A0_B2_REVISION, PIPELINE_ID, _CONFIG_HASH, extract_relations_b2,
)

CRITICAL = (
    "direct", "reordered", "possessive", "apposition", "ter_como",
    "contracted_preposition", "discontinuous", "coordination", "multiple_relations",
    "reported", "spouse_surface", "sibling", "parent_child", "narrator",
)


def oracle_target(case: dict, item: dict, side: str) -> str:
    """Return explicit B.3 target or conservatively infer legacy oracle semantics."""
    explicit = item.get(f"endpoint_{side}_semantic_target")
    if explicit:
        return explicit
    mention = (item.get(f"endpoint_{side}_mention") or "").casefold()
    if "narrator" in case.get("tags", []) and mention in {"meu", "minha"}:
        return "NARRATOR_ROLE"
    if mention in {"ele", "ela", "dele", "dela"} or not mention:
        return "UNRESOLVED_MENTION"
    return "EXPLICIT_MENTION"


def match(expected: list[dict], predicted: list[dict]):
    used = set()
    for oracle in expected:
        options = [
            index for index, item in enumerate(predicted)
            if index not in used and item["relation_type"] == oracle["relation_type"]
            and item["relation_surface_text"].casefold() == oracle["relation_surface_text"].casefold()
        ]
        if options:
            used.add(options[0])
            yield oracle, predicted[options[0]]


def augment(rows: list[dict], metrics: dict) -> dict:
    """Add narrator and graph-boundary safety metrics to established B.2 metrics."""
    wrong_narrator = 0
    narrator_total = 0
    narrator_correct = 0
    for row in rows:
        case = row["case"]
        for oracle, predicted in match(case["expected_relation_candidates"], row["result"]["candidates"]):
            for side in ("a", "b"):
                expected_target = oracle_target(case, oracle, side)
                if expected_target == "NARRATOR_ROLE":
                    narrator_total += 1
                    if predicted.get(f"endpoint_{side}_semantic_target") == expected_target:
                        narrator_correct += 1
                    else:
                        wrong_narrator += 1
    graph_autobind = sum(
        1 for row in rows for item in row["result"]["candidates"]
        for field in item if "person_id" in field.casefold()
    )
    metrics["b3_safety"] = {
        "wrong_narrator_role_resolution": wrong_narrator,
        "graph_person_autobind_from_narrator": graph_autobind,
        "narrator_targets_expected": narrator_total,
        "narrator_targets_correct": narrator_correct,
        "reported_mode_lost": metrics["failure_taxonomy"].get("REPORTED_MODE_LOST", 0),
    }
    return metrics


def evaluate(cases: list[dict]):
    rows, metrics = b2.evaluate(cases, "A0_B2")
    return rows, augment(rows, metrics)


def r4_b3(cases: list[dict], metrics: dict) -> dict:
    """Apply R4, marking sparse unseen family denominators explicitly."""
    expected_by_tag = Counter()
    for case in cases:
        for tag in case["tags"]:
            expected_by_tag[tag] += len(case["expected_relation_candidates"])
    per_tag = metrics["coverage"]["per_phenomenon_recall"]
    phenomenon = {}
    populated = []
    for tag in CRITICAL:
        denominator = expected_by_tag[tag]
        if denominator < 2:
            phenomenon[tag] = {"status": "N/A_SMALL_DENOMINATOR", "denominator": denominator,
                               "recall": per_tag.get(tag)}
        else:
            recall = per_tag.get(tag, 0.0)
            populated.append(recall)
            phenomenon[tag] = {"status": "PASS" if recall >= 0.20 else "FAIL",
                               "denominator": denominator, "recall": recall}
    type_values = metrics["coverage"]["per_relation_type_recall"]
    checks = {
        "persistible_oracle_recall": metrics["coverage"]["persistible_oracle_recall"] >= 0.50,
        "every_relation_type": bool(type_values) and min(type_values.values()) >= 0.30,
        "populated_critical_phenomena": bool(populated) and min(populated) >= 0.20,
    }
    return {
        "checks": checks, "overall": all(checks.values()), "phenomena": phenomenon,
        "minimum_relation_type_value": min(type_values.values()) if type_values else None,
        "minimum_populated_critical_value": min(populated) if populated else None,
    }


def write_json(name: str, payload):
    (HERE / name).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=("existing", "unseen", "all"), default="all")
    args = parser.parse_args()
    tuning = b2.load("tuning_cases.json")
    challenge = b2.load("challenge_cases.json")
    if args.phase in {"existing", "all"}:
        combined = tuning + challenge
        rows, metrics = evaluate(combined)
        _, challenge_metrics = evaluate(challenge)
        write_json("metrics_existing.json", {"metrics": metrics, "r4": r4_b3(combined, metrics)})
        write_json("metrics_b2_challenge.json", {"metrics": challenge_metrics,
                                                  "r4": r4_b3(challenge, challenge_metrics)})
        print(json.dumps({"existing": metrics["end_to_end"], "b3": metrics["b3_safety"],
                          "r4": r4_b3(combined, metrics)["overall"]}))
    if args.phase in {"unseen", "all"}:
        unseen_path = HERE / "checkpoint_b3_unseen.jsonl"
        unseen, digest = validation.load_and_validate(unseen_path)
        rows, metrics = evaluate(unseen)
        gate = r4_b3(unseen, metrics)
        write_json("predictions_unseen.json", rows)
        write_json("metrics_unseen.json", {"metrics": metrics, "r4": gate})
        manifest = {
            "corpus": unseen_path.name, "sha256": digest, "narratives": len(unseen),
            "expected_candidates": sum(len(c["expected_relation_candidates"]) for c in unseen),
            "configuration_hash": _CONFIG_HASH, "pipeline_id": PIPELINE_ID,
            "evaluation_sequence": "oracle generated -> structural validation -> SHA-256 -> one-shot prediction",
        }
        write_json("unseen_manifest.json", manifest)
        safety = metrics["end_to_end"]["wrong_resolved_endpoint"] == 0 and metrics["end_to_end"]["unsafe_persistible_false_positive"] == 0
        ready = safety and gate["overall"] and metrics["b3_safety"]["reported_mode_lost"] == 0 and metrics["b3_safety"]["wrong_narrator_role_resolution"] == 0
        freeze = {
            "pipeline_id": PIPELINE_ID, "source_checkpoint": "B.3",
            "detector_architecture": "deterministic structural A0_B2 with B.3 semantic guards",
            "detector_model_id": A0_B2_MODEL_ID, "parser_guard_revision": A0_B2_REVISION + "+B3",
            "configuration_hash": _CONFIG_HASH,
            "supported_relation_types": sorted(validation.RELATIONS),
            "narrator_endpoint_semantics": "NARRATOR_ROLE; no graph identity",
            "reporting_semantics": "sentence-local reporting verbs and named source introductions",
            "b3_unseen_corpus_sha256": digest, "b3_unseen_results": metrics,
            "r4": gate, "readiness_status": "READY_FOR_REVIEW_INTEGRATION" if ready else "NOT_READY_FOR_REVIEW_INTEGRATION",
        }
        write_json("extraction_freeze.json", freeze)
        print(json.dumps({"unseen": metrics["end_to_end"], "b3": metrics["b3_safety"],
                          "r4": gate["overall"], "status": freeze["readiness_status"]}))


if __name__ == "__main__":
    main()
