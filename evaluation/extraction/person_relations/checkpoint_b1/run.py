"""Run the development-only Checkpoint B.1 detector comparison."""

from __future__ import annotations

import json
import importlib.util
import sys
from collections import Counter, defaultdict
from pathlib import Path
from time import perf_counter

from gliner2 import AutoExtractor


HERE = Path(__file__).resolve().parent
RELATION_ROOT = HERE.parent
ROOT = HERE.parents[3]
CHECKPOINT_B = HERE.parent / "checkpoint_b"
GLINER_APP = ROOT / "gliner-service"
for path in (CHECKPOINT_B, GLINER_APP):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

_checkpoint_b_spec = importlib.util.spec_from_file_location(
    "lifegraph_checkpoint_b_run", CHECKPOINT_B / "run.py"
)
assert _checkpoint_b_spec and _checkpoint_b_spec.loader
checkpoint_b = importlib.util.module_from_spec(_checkpoint_b_spec)
_checkpoint_b_spec.loader.exec_module(checkpoint_b)
from app.model import MODEL_ID, MODEL_REVISION  # noqa: E402
from app.relation_extraction import GENERIC_LABELS, SPECIFIC_LABELS  # noqa: E402


CORPORA = (
    RELATION_ROOT / "v1_adversarial.jsonl",
    RELATION_ROOT / "checkpoint_b_expansion.jsonl",
    RELATION_ROOT / "checkpoint_b1_generalization.jsonl",
)
THRESHOLDS = checkpoint_b.THRESHOLDS
CRITICAL_TAGS = (
    "reordered", "possessive", "apposition", "reported", "uncertain",
    "negated", "question", "quoted_language", "incidental_kinship",
    "metaphor", "coordination", "pronoun", "partial_endpoint", "distractor_heavy",
)


def load_cases() -> list[dict]:
    """Load only the three relation-development corpora."""
    return [
        json.loads(line)
        for path in CORPORA
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def is_partial(case: dict, oracle: dict) -> bool:
    """Return whether the oracle permits or requires endpoint abstention."""
    return (
        oracle["endpoint_a_mention"] is None
        or oracle["endpoint_b_mention"] is None
        or "partial_endpoint" in case["tags"]
        or "pronoun" in case["tags"]
    )


def b1_metrics(rows: list[dict]) -> dict:
    """Extend Checkpoint B metrics with coverage and abstention observability."""
    base = checkpoint_b.score(rows)
    type_counts: defaultdict[str, Counter] = defaultdict(Counter)
    tag_counts: defaultdict[str, Counter] = defaultdict(Counter)
    persistible_expected = persistible_correct = 0
    safe_abstention = unnecessary_abstention = 0
    partial_opportunities = resolution_opportunities = 0
    total_misses = 0

    for row in rows:
        case = row["case"]
        expected = case["expected_relation_candidates"]
        predicted = row["result"]["candidates"]
        pairs, missing, _ = checkpoint_b.match_candidates(expected, predicted)
        total_misses += len(missing)
        pair_by_expected = dict(pairs)
        for index, oracle in enumerate(expected):
            relation_type = oracle["relation_type"]
            type_counts[relation_type]["expected"] += 1
            for tag in case["tags"]:
                tag_counts[tag]["expected"] += 1
            if oracle["persistible_in_v1"]:
                persistible_expected += 1
            if index not in pair_by_expected:
                continue
            item = predicted[pair_by_expected[index]]
            a_match = (item["endpoint_a_mention"] or "").casefold() == (oracle["endpoint_a_mention"] or "").casefold()
            b_match = (item["endpoint_b_mention"] or "").casefold() == (oracle["endpoint_b_mention"] or "").casefold()
            correct = a_match and b_match
            if correct:
                type_counts[relation_type]["correct"] += 1
                for tag in case["tags"]:
                    tag_counts[tag]["correct"] += 1
            if oracle["persistible_in_v1"] and correct and item["persistence_eligibility"] == "LINGUISTICALLY_ELIGIBLE_REVIEW_AND_BINDING_REQUIRED":
                persistible_correct += 1
            unresolved = "UNRESOLVED_MENTION" in {
                item["endpoint_a_resolution_state"], item["endpoint_b_resolution_state"]
            }
            if is_partial(case, oracle):
                partial_opportunities += 1
                if unresolved:
                    safe_abstention += 1
            else:
                resolution_opportunities += 1
                if unresolved:
                    unnecessary_abstention += 1

    ratio = checkpoint_b.ratio
    base["coverage"] = {
        "persistible_oracle_expected": persistible_expected,
        "persistible_oracle_correct": persistible_correct,
        "persistible_oracle_recall": ratio(persistible_correct, persistible_expected),
        "per_relation_type_recall": {
            key: ratio(value["correct"], value["expected"])
            for key, value in sorted(type_counts.items())
        },
        "per_phenomenon_recall": {
            key: ratio(value["correct"], value["expected"])
            for key, value in sorted(tag_counts.items())
        },
        "safe_abstention_count": safe_abstention,
        "safe_abstention_rate": ratio(safe_abstention, partial_opportunities),
        "unnecessary_abstention_count": unnecessary_abstention,
        "unnecessary_abstention_rate": ratio(unnecessary_abstention, resolution_opportunities),
        "total_detector_candidate_miss": total_misses,
    }
    return base


def evaluate(cases: list[dict], strategy: str, threshold: float, raw_outputs: dict[str, dict] | None = None) -> tuple[list[dict], dict]:
    """Evaluate one detector with shared Checkpoint B downstream logic."""
    rows, _ = checkpoint_b.evaluate(cases, strategy, threshold, raw_outputs)
    return rows, b1_metrics(rows)


def configuration_key(metrics: dict, threshold: float) -> tuple:
    """Rank safely, then by coverage, then by the remaining frozen criteria."""
    end = metrics["end_to_end"]
    coverage = metrics["coverage"]
    return (
        end["unsafe_persistible_false_positive"],
        end["wrong_resolved_endpoint"],
        -coverage["persistible_oracle_recall"],
        end["false_relation_candidates"],
        -end["precision"],
        -end["both_endpoint_accuracy"],
        -end["relation_type_accuracy"],
        -end["recall"],
        -end["f1"],
        -threshold,
    )


def write_json(name: str, value: object) -> None:
    """Write a reproducible UTF-8 development artifact."""
    (HERE / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    """Run A0 and one bounded threshold sweep for B and C."""
    cases = load_cases()
    started = perf_counter()
    a0_rows, a0_metrics = evaluate(cases, "A0", 1.0)
    print("A0_ORIGINAL complete", flush=True)
    model = AutoExtractor.from_pretrained(MODEL_ID, revision=MODEL_REVISION, map_location="cpu")
    raw = {
        "B": checkpoint_b.model_outputs(model, cases, SPECIFIC_LABELS, "B"),
        "C": checkpoint_b.model_outputs(model, cases, GENERIC_LABELS, "C"),
    }
    sweep: dict[str, list[dict]] = {}
    selected = {"A0_ORIGINAL": {"threshold": 1.0, "metrics": a0_metrics}}
    selected_rows = {"A0_ORIGINAL": a0_rows}
    for strategy in ("B", "C"):
        evaluated = []
        rows_by_threshold = {}
        for threshold in THRESHOLDS:
            rows, metrics = evaluate(cases, strategy, threshold, raw[strategy])
            evaluated.append((threshold, metrics))
            rows_by_threshold[threshold] = rows
        threshold, metrics = min(evaluated, key=lambda item: configuration_key(item[1], item[0]))
        selected[strategy] = {"threshold": threshold, "metrics": metrics}
        selected_rows[strategy] = rows_by_threshold[threshold]
        sweep[strategy] = [{"threshold": threshold, "metrics": metrics} for threshold, metrics in evaluated]

    generalization = [case for case in cases if "b1_generalization" in case["tags"]]
    a0_generalization_rows, a0_generalization = evaluate(generalization, "A0", 1.0)
    novelty = {
        "new_narratives": len(generalization),
        "new_candidates": sum(len(case["expected_relation_candidates"]) for case in generalization),
        "a0_original_detected_cases": sum(bool(row["result"]["detections"]) for row in a0_generalization_rows),
        "a0_original_nonmatching_cases": sum(not row["result"]["detections"] for row in a0_generalization_rows),
        "syntactic_template_families": len({tag for case in generalization for tag in case["tags"] if tag not in {"b1_generalization", "persistible_oracle", "negative_control", "no_relation"}}),
        "a0_generalization_metrics": a0_generalization,
    }
    config = {
        "development_only": True,
        "corpus_files": [str(path.relative_to(ROOT)) for path in CORPORA],
        "narratives": len(cases),
        "expected_candidates": sum(len(case["expected_relation_candidates"]) for case in cases),
        "model_id": MODEL_ID,
        "model_revision": MODEL_REVISION,
        "specific_labels": SPECIFIC_LABELS,
        "generic_labels": GENERIC_LABELS,
        "threshold_grid": THRESHOLDS,
        "shared_downstream": True,
        "critical_tags": CRITICAL_TAGS,
    }
    write_json("experiment_config.json", config)
    write_json("threshold_sweep.json", sweep)
    write_json("metrics.json", selected)
    write_json("generalization_metrics.json", novelty)
    for strategy, rows in selected_rows.items():
        write_json(f"predictions_{strategy}.json", rows)
    write_json("execution_summary.json", {
        "elapsed_seconds": round(perf_counter() - started, 3),
        "selected_thresholds": {key: value["threshold"] for key, value in selected.items()},
    })
    print(json.dumps({key: {"end_to_end": value["metrics"]["end_to_end"], "coverage": value["metrics"]["coverage"]} for key, value in selected.items()}, indent=2))


if __name__ == "__main__":
    main()
