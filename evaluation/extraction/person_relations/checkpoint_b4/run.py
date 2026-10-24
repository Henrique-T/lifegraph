"""Checkpoint B.4 regression and one-shot micro-challenge evaluation."""

from __future__ import annotations

import argparse
import copy
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
B3 = HERE.parent / "checkpoint_b3"
B2 = HERE.parent / "checkpoint_b2"
GLINER_APP = ROOT / "gliner-service"
for path in (GLINER_APP, B3, B2):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


b3 = load_module("lifegraph_b3_for_b4", B3 / "run.py")
b2 = b3.b2
validation = load_module("lifegraph_b4_validation", HERE / "unseen_validation.py")

from app.relation_extraction_b2 import (  # noqa: E402
    A0_B2_MODEL_ID, A0_B2_REVISION, PIPELINE_ID, _CONFIG_HASH, extract_relations_b2,
)

ELIGIBLE = "LINGUISTICALLY_ELIGIBLE_REVIEW_AND_BINDING_REQUIRED"


def write_json(name, value):
    (HERE / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def pairs(expected, predicted):
    used = set()
    for oracle in expected:
        choices = [
            i for i, item in enumerate(predicted) if i not in used
            and item["relation_type"] == oracle["relation_type"]
            and item["relation_surface_text"].casefold() == oracle["relation_surface_text"].casefold()
        ]
        if choices:
            used.add(choices[0])
            yield oracle, predicted[choices[0]]


def question_metrics(rows):
    metrics = {key: 0 for key in (
        "QUESTION_RELATION_CANDIDATE", "QUESTION_CORRECTLY_BLOCKED",
        "QUESTION_UNSAFE_PERSISTIBLE", "QUESTION_WRONG_ENDPOINT", "QUESTION_FALSE_RELATION",
    )}
    for row in rows:
        if "?" not in row["case"]["narrative"]:
            continue
        expected = row["case"]["expected_relation_candidates"]
        predicted = row["result"]["candidates"]
        metrics["QUESTION_RELATION_CANDIDATE"] += len(predicted)
        metrics["QUESTION_CORRECTLY_BLOCKED"] += sum(item["persistence_eligibility"] != ELIGIBLE for item in predicted)
        metrics["QUESTION_UNSAFE_PERSISTIBLE"] += sum(item["persistence_eligibility"] == ELIGIBLE for item in predicted)
        matched = list(pairs(expected, predicted))
        for oracle, item in matched:
            if ((oracle.get("endpoint_a_mention") or "").casefold() != (item.get("endpoint_a_mention") or "").casefold()
                    or (oracle.get("endpoint_b_mention") or "").casefold() != (item.get("endpoint_b_mention") or "").casefold()):
                metrics["QUESTION_WRONG_ENDPOINT"] += 1
        metrics["QUESTION_FALSE_RELATION"] += max(0, len(predicted) - len(matched))
    return metrics


def relative_metrics(rows):
    oracle_total = recovered = wrong = unsafe = 0
    for row in rows:
        if "relative_apposition" not in row["case"]["tags"]:
            continue
        expected = row["case"]["expected_relation_candidates"]
        predicted = row["result"]["candidates"]
        oracle_total += len(expected)
        matched = list(pairs(expected, predicted))
        recovered += len(matched)
        for oracle, item in matched:
            if ((oracle.get("endpoint_a_mention") or "").casefold() != (item.get("endpoint_a_mention") or "").casefold()
                    or (oracle.get("endpoint_b_mention") or "").casefold() != (item.get("endpoint_b_mention") or "").casefold()):
                wrong += 1
            if not oracle.get("persistible_in_v1", False) and item["persistence_eligibility"] == ELIGIBLE:
                unsafe += 1
    return {"oracle_positives": oracle_total, "recovered": recovered,
            "recall": round(recovered / oracle_total, 6) if oracle_total else None,
            "wrong_endpoint": wrong, "unsafe_persistible": unsafe}


def evaluate(cases):
    rows, metrics = b3.evaluate(cases)
    metrics["question_metrics"] = question_metrics(rows)
    metrics["relative_apposition_metrics"] = relative_metrics(rows)
    return rows, metrics, b3.r4_b3(cases, metrics)


def b3_regression_cases():
    path = B3 / "checkpoint_b3_unseen.jsonl"
    cases, _ = b3.validation.load_and_validate(path)
    cases = copy.deepcopy(cases)
    replacements = {
        "B3-U-034": {
            "relation_type": "FATHER_OF", "relation_surface_text": "pai de",
            "endpoint_a_mention": "Ele", "endpoint_b_mention": "Marina",
            "endpoint_a_semantic_target": "UNRESOLVED_MENTION", "endpoint_b_semantic_target": "EXPLICIT_MENTION",
            "polarity": "POSITIVE", "epistemic_status": "UNCERTAIN", "reporting_mode": "DIRECT",
            "temporal_scope": "CURRENT_OR_UNSPECIFIED", "interrogative": True,
            "persistible_in_v1": False, "rationale": "Blocked interrogative relation mention under B.4 policy.",
        },
        "B3-U-036": {
            "relation_type": "FATHER_OF", "relation_surface_text": "pai de",
            "endpoint_a_mention": "Quem", "endpoint_b_mention": "Laura",
            "endpoint_a_semantic_target": "UNRESOLVED_MENTION", "endpoint_b_semantic_target": "EXPLICIT_MENTION",
            "polarity": "POSITIVE", "epistemic_status": "UNCERTAIN", "reporting_mode": "DIRECT",
            "temporal_scope": "CURRENT_OR_UNSPECIFIED", "interrogative": True,
            "persistible_in_v1": False, "rationale": "WH endpoint remains linguistically unresolved.",
        },
    }
    for case in cases:
        if case["case_id"] in replacements:
            case["expected_relation_candidates"] = [replacements[case["case_id"]]]
            case["tags"] = sorted(set(case["tags"] + ["question", "b4_question_policy"]))
        if case["case_id"] in {"B3-U-008", "B3-U-009"}:
            case["tags"] = sorted(set(case["tags"] + ["relative_apposition", "b4_regression"]))
    return cases


def save_result(prefix, cases):
    rows, metrics, gate = evaluate(cases)
    write_json(f"metrics_{prefix}.json", {"metrics": metrics, "r4": gate})
    return rows, metrics, gate


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=("regression", "unseen", "all"), default="all")
    args = parser.parse_args()
    if args.phase in {"regression", "all"}:
        tuning = b2.load("tuning_cases.json")
        challenge = b2.load("challenge_cases.json")
        _, existing, existing_gate = save_result("existing", tuning + challenge)
        _, b2_metrics, b2_gate = save_result("b2_challenge", challenge)
        _, b3_metrics, b3_gate = save_result("b3_regression", b3_regression_cases())
        print(json.dumps({"existing_r4": existing_gate["overall"], "b2_r4": b2_gate["overall"],
                          "b3_r4": b3_gate["overall"], "b3_questions": b3_metrics["question_metrics"],
                          "b3_relative": b3_metrics["relative_apposition_metrics"]}))
    if args.phase in {"unseen", "all"}:
        unseen_path = HERE / "checkpoint_b4_unseen.jsonl"
        unseen, digest = validation.validate(unseen_path)
        rows, metrics, gate = save_result("b4_unseen", unseen)
        write_json("predictions_b4_unseen.json", rows)
        manifest = {"corpus": unseen_path.name, "sha256": digest, "narratives": len(unseen),
                    "expected_candidates": sum(len(c["expected_relation_candidates"]) for c in unseen),
                    "configuration_hash": _CONFIG_HASH,
                    "sequence": "code freeze -> oracle validation -> SHA-256 -> one-shot prediction"}
        write_json("unseen_manifest.json", manifest)
        end, qm, rm, b3s = metrics["end_to_end"], metrics["question_metrics"], metrics["relative_apposition_metrics"], metrics["b3_safety"]
        ready = (
            end["wrong_resolved_endpoint"] == 0 and end["unsafe_persistible_false_positive"] == 0
            and qm["QUESTION_UNSAFE_PERSISTIBLE"] == 0 and qm["QUESTION_WRONG_ENDPOINT"] == 0
            and b3s["wrong_narrator_role_resolution"] == 0 and b3s["graph_person_autobind_from_narrator"] == 0
            and b3s["reported_mode_lost"] == 0 and gate["overall"]
            and rm["wrong_endpoint"] == 0 and rm["unsafe_persistible"] == 0
            and (rm["oracle_positives"] < 3 or rm["recall"] >= 0.5)
        )
        freeze = {
            "pipeline_id": PIPELINE_ID, "configuration_hash": _CONFIG_HASH,
            "source_checkpoint": "B.4", "primary_relation_detector": "DETERMINISTIC_STRUCTURAL",
            "gliner_primary_relation_detector": False, "gliner_fallback": False,
            "model_id": A0_B2_MODEL_ID, "revision": A0_B2_REVISION,
            "supported_relation_types": sorted(validation.RELATIONS),
            "supported_structural_families": ["direct", "reordered", "nominal_apposition", "relative_apposition", "ter_como", "discontinuous", "coordination", "interrogative"],
            "question_semantics": "RelationCandidate allowed; epistemic UNCERTAIN; never linguistically persistible",
            "narrator_semantics": "NARRATOR_ROLE without graph identity",
            "reporting_semantics": "sentence-local reporting verbs and named source introductions",
            "safety_gates": {"wrong_resolved_endpoint": 0, "unsafe_persistible_false_positive": 0,
                             "question_unsafe_persistible": 0, "wrong_narrator_role_resolution": 0,
                             "graph_person_autobind_from_narrator": 0, "reported_mode_lost": 0},
            "r4": gate, "b4_unseen_sha256": digest, "b4_unseen_metrics": metrics,
            "history": {"B3": "NOT_READY_FOR_REVIEW_INTEGRATION: relative apposition 0/2",
                        "B4": "one-shot micro-challenge"},
            "readiness_status": "READY_FOR_REVIEW_INTEGRATION" if ready else "NOT_READY_FOR_REVIEW_INTEGRATION",
        }
        write_json("extraction_freeze.json", freeze)
        print(json.dumps({"metrics": end, "question": qm, "relative": rm,
                          "r4": gate["overall"], "status": freeze["readiness_status"]}))


if __name__ == "__main__":
    main()
