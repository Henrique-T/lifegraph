"""Execute the Checkpoint B.2 tuning/challenge detector comparison."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from time import perf_counter

from gliner2 import AutoExtractor


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
GLINER_APP = ROOT / "gliner-service"
B1 = HERE.parent / "checkpoint_b1"
B = HERE.parent / "checkpoint_b"
for path in (GLINER_APP, B1, B):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


def load_module(name: str, path: Path):
    """Load an evaluation module without ambiguous `run` imports."""
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


b1 = load_module("lifegraph_b1_run_for_b2", B1 / "run.py")
b0 = b1.checkpoint_b

from app.model import MODEL_ID, MODEL_REVISION  # noqa: E402
from app.relation_extraction import GENERIC_LABELS, SPECIFIC_LABELS  # noqa: E402
from app.relation_extraction_b2 import D1_LABELS, extract_relations_b2  # noqa: E402


THRESHOLDS = b0.THRESHOLDS
CRITICAL = (
    "direct", "reordered", "possessive", "apposition", "existential_have",
    "contracted_preposition", "discontinuous", "coordination", "multiple_relations",
    "reported", "spouse_surface", "sibling", "persistible_oracle",
)


def load(name: str) -> list[dict]:
    """Read a frozen B.2 split artifact."""
    return json.loads((HERE / name).read_text(encoding="utf-8"))


def evaluate(cases: list[dict], strategy: str, threshold: float = 1.0,
             raw: dict[str, dict] | None = None) -> tuple[list[dict], dict]:
    """Run a B.2 detector through the shared structural pipeline."""
    rows = []
    for case in cases:
        result = extract_relations_b2(
            case["narrative"], case["case_id"], strategy, threshold,
            raw.get(case["case_id"]) if raw else None,
        ).model_dump(mode="json")
        rows.append({"case": case, "result": result})
    return rows, b1.b1_metrics(rows)


def r4(metrics: dict) -> dict:
    """Apply the frozen B.1 development minima to positive families only."""
    coverage = metrics["coverage"]
    available = [coverage["per_phenomenon_recall"].get(tag, 0.0) for tag in CRITICAL]
    checks = {
        "persistible_oracle_recall": coverage["persistible_oracle_recall"] >= 0.50,
        "minimum_relation_type_recall": min(coverage["per_relation_type_recall"].values()) >= 0.30,
        "minimum_critical_phenomenon_recall": min(available) >= 0.20,
    }
    checks["overall"] = all(checks.values())
    checks["minimum_relation_type_value"] = min(coverage["per_relation_type_recall"].values())
    checks["minimum_critical_phenomenon_value"] = min(available)
    return checks


def safety(metrics: dict) -> bool:
    """Apply both non-negotiable safety gates."""
    end = metrics["end_to_end"]
    return end["wrong_resolved_endpoint"] == 0 and end["unsafe_persistible_false_positive"] == 0


def choose(evaluated: list[tuple[float, list[dict], dict]]) -> tuple[float, list[dict], dict]:
    """Rank thresholds by safety, coverage, and then the frozen quality criteria."""
    def key(item):
        threshold, _, metrics = item
        end, coverage, gate = metrics["end_to_end"], metrics["coverage"], r4(metrics)
        return (
            not safety(metrics), not gate["overall"],
            end["unsafe_persistible_false_positive"], end["wrong_resolved_endpoint"],
            -coverage["persistible_oracle_recall"], end["false_relation_candidates"],
            -end["precision"], -end["both_endpoint_accuracy"], -end["relation_type_accuracy"],
            -end["recall"], -end["f1"], -threshold,
        )
    return min(evaluated, key=key)


def model_outputs(model, cases: list[dict], labels: dict, label: str) -> dict[str, dict]:
    """Run one label configuration once at the lowest threshold."""
    result = {}
    for index, case in enumerate(cases, 1):
        result[case["case_id"]] = model.extract_entities(
            case["narrative"], labels, threshold=min(THRESHOLDS),
            include_confidence=True, include_spans=True,
        )
        if index % 25 == 0:
            print(f"{label}: {index}/{len(cases)}", flush=True)
    return result


def write(name: str, value: object) -> None:
    """Write one reproducible result artifact."""
    (HERE / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def subset(rows: list[dict], ids: set[str]) -> list[dict]:
    """Select prediction rows by frozen case identifier."""
    return [row for row in rows if row["case"]["case_id"] in ids]


def main() -> None:
    """Evaluate historical A0 and B.2 A0/B/C/D1 on both frozen splits."""
    tuning, challenge = load("tuning_cases.json"), load("challenge_cases.json")
    combined = tuning + challenge
    tuning_ids = {case["case_id"] for case in tuning}
    challenge_ids = {case["case_id"] for case in challenge}
    started = perf_counter()

    historical_rows = json.loads((B1 / "predictions_A0_ORIGINAL.json").read_text(encoding="utf-8"))
    historical = {
        "tuning": b1.b1_metrics(subset(historical_rows, tuning_ids)),
        "challenge": b1.b1_metrics(subset(historical_rows, challenge_ids)),
        "combined": b1.b1_metrics(historical_rows),
    }

    all_results = {"A0_ORIGINAL": {"threshold": 1.0, **historical}}
    predictions: dict[str, dict[str, list[dict]]] = {}
    a0_splits = {}
    for split_name, cases in (("tuning", tuning), ("challenge", challenge), ("combined", combined)):
        rows, metrics = evaluate(cases, "A0_B2")
        a0_splits[split_name] = metrics
        predictions.setdefault("A0_B2", {})[split_name] = rows
    all_results["A0_B2"] = {"threshold": 1.0, **a0_splits}

    model = AutoExtractor.from_pretrained(MODEL_ID, revision=MODEL_REVISION, map_location="cpu")
    configs = {"B_B2": ("B", SPECIFIC_LABELS), "C_B2": ("C", GENERIC_LABELS), "D1": ("D1", D1_LABELS)}
    sweep = {}
    for config_name, (strategy, labels) in configs.items():
        raw = model_outputs(model, combined, labels, config_name)
        evaluated = []
        for threshold in THRESHOLDS:
            rows, metrics = evaluate(combined, strategy, threshold, raw)
            evaluated.append((threshold, rows, metrics))
        threshold, combined_rows, combined_metrics = choose(evaluated)
        tuning_rows, challenge_rows = subset(combined_rows, tuning_ids), subset(combined_rows, challenge_ids)
        all_results[config_name] = {
            "threshold": threshold,
            "tuning": b1.b1_metrics(tuning_rows),
            "challenge": b1.b1_metrics(challenge_rows),
            "combined": combined_metrics,
        }
        predictions[config_name] = {"tuning": tuning_rows, "challenge": challenge_rows, "combined": combined_rows}
        sweep[config_name] = [{
            "threshold": value, "metrics": metrics, "safety_pass": safety(metrics), "r4": r4(metrics)
        } for value, _, metrics in evaluated]

    for value in all_results.values():
        for split_name in ("tuning", "challenge", "combined"):
            value[split_name]["safety_pass"] = safety(value[split_name])
            value[split_name]["r4"] = r4(value[split_name])
    write("metrics_all.json", all_results)
    write("metrics_tuning.json", {key: value["tuning"] for key, value in all_results.items()})
    write("metrics_challenge.json", {key: value["challenge"] for key, value in all_results.items()})
    write("metrics_combined.json", {key: value["combined"] for key, value in all_results.items()})
    write("threshold_sweep.json", sweep)
    for strategy, split_rows in predictions.items():
        write(f"predictions_{strategy}.json", split_rows)
    write("experiment_config.json", {
        "development_only": True, "model_id": MODEL_ID, "model_revision": MODEL_REVISION,
        "threshold_grid": THRESHOLDS, "specific_labels": SPECIFIC_LABELS,
        "generic_labels": GENERIC_LABELS, "d1_labels": D1_LABELS,
        "critical_positive_phenomena": CRITICAL, "shared_b2_downstream": True,
        "elapsed_seconds": round(perf_counter() - started, 3),
    })
    print(json.dumps({key: {
        "threshold": value["threshold"], "combined_safety": value["combined"]["safety_pass"],
        "combined_r4": value["combined"]["r4"], "challenge_safety": value["challenge"]["safety_pass"],
        "challenge_r4": value["challenge"]["r4"], "combined_end": value["combined"]["end_to_end"],
    } for key, value in all_results.items()}, indent=2))


if __name__ == "__main__":
    main()
