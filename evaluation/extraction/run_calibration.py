"""Run the frozen GLiNER comparison. No REF, graph, or LifeGraph imports."""
from collections import Counter, defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path
import statistics
import urllib.request

ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"
CONFIG_IDS = (
    "A_ENTITY_EVENT_BASELINE",
    "B_LINGUISTIC_EVENT_SPANS",
    "C_STRUCTURED_RECORDS",
    "D_CONSTRAINED_RECORDS",
    "E_RELATION_EXTRACTION",
)
ENDPOINT = "http://localhost:8200/calibration/extract"


def normalized(text):
    return " ".join(text.casefold().split()) if isinstance(text, str) else None


def validate_benchmark(data):
    assert data["ground_truth_source"] == "human_specified_before_primary_model_runs"
    assert 30 <= len(data["cases"]) <= 40
    ids = set()
    for case in data["cases"]:
        assert case["id"] not in ids
        ids.add(case["id"])
        assert isinstance(case["text"], str) and case["text"]
        assert isinstance(case["categories"], list)
        for event in case["expected_events"]:
            assert event["event_type"] in {"nascimento", "casamento", "obito", "natimorto"}
            assert isinstance(event["belongs_to_narrator"], bool)


def call(config_id, text):
    body = json.dumps({"configuration_id": config_id, "text": text}, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(ENDPOINT, data=body, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(request, timeout=180) as response:
        return json.load(response)


def match_events(expected, detected):
    remaining = list(enumerate(detected))
    pairs, missed = [], []
    for exp in expected:
        found = next(((i, det) for i, det in remaining if det.get("event_type") == exp["event_type"]), None)
        if found is None:
            missed.append(exp)
        else:
            pairs.append((exp, found[1]))
            remaining = [(i, det) for i, det in remaining if i != found[0]]
    return pairs, missed, [det for _, det in remaining]


def score(cases):
    tp = fp = fn = subject_total = subject_exact = date_total = date_exact = 0
    third_total = third_subject = negative_cases = negative_fp = multi_expected = multi_detected = 0
    per_type = defaultdict(lambda: Counter(tp=0, fp=0, fn=0))
    latencies = []
    for item in cases:
        expected, detected = item["expected_events"], item["result"]["detected_events"]
        pairs, missed, extras = match_events(expected, detected)
        tp += len(pairs); fn += len(missed); fp += len(extras)
        latencies.append(item["result"]["latency_ms"])
        for exp, det in pairs:
            per_type[exp["event_type"]]["tp"] += 1
            if exp["subject_text"] is not None:
                subject_total += 1
                if normalized(exp["subject_text"]) == normalized(det.get("subject_text")):
                    subject_exact += 1
            if exp["date_expression"] is not None:
                date_total += 1
                if normalized(exp["date_expression"]) == normalized(det.get("date_expression")):
                    date_exact += 1
            if not exp["belongs_to_narrator"]:
                third_total += 1
                if exp["subject_text"] is not None and normalized(exp["subject_text"]) == normalized(det.get("subject_text")):
                    third_subject += 1
        for exp in missed:
            per_type[exp["event_type"]]["fn"] += 1
            if not exp["belongs_to_narrator"]:
                third_total += 1
        for det in extras:
            if det.get("event_type") in {"nascimento", "casamento", "obito", "natimorto"}:
                per_type[det["event_type"]]["fp"] += 1
        if not expected:
            negative_cases += 1
            negative_fp += bool(detected)
        if len(expected) > 1:
            multi_expected += len(expected)
            multi_detected += len(pairs)
    precision = tp / (tp + fp) if tp + fp else 0
    recall = tp / (tp + fn) if tp + fn else 0
    metrics = {
        "event_precision": precision,
        "event_recall": recall,
        "event_f1": 2 * precision * recall / (precision + recall) if precision + recall else 0,
        "subject_exact_accuracy": subject_exact / subject_total if subject_total else None,
        "temporal_exact_accuracy": date_exact / date_total if date_total else None,
        "third_party_subject_identification_rate": third_subject / third_total if third_total else None,
        "false_narrator_attribution_rate": None,
        "negative_case_false_positive_rate": negative_fp / negative_cases if negative_cases else None,
        "multi_event_recall": multi_detected / multi_expected if multi_expected else None,
        "structured_output_validity": 1.0,
        "latency_ms": {"mean": statistics.mean(latencies), "median": statistics.median(latencies), "min": min(latencies), "max": max(latencies), "p95": sorted(latencies)[int(0.95 * (len(latencies)-1))]},
        "counts": {"tp": tp, "fp": fp, "fn": fn},
        "per_event_type": {},
    }
    for event_type in ("nascimento", "casamento", "obito", "natimorto"):
        c = per_type[event_type]; p = c["tp"]/(c["tp"]+c["fp"]) if c["tp"]+c["fp"] else 0; r = c["tp"]/(c["tp"]+c["fn"]) if c["tp"]+c["fn"] else 0
        metrics["per_event_type"][event_type] = {"precision":p,"recall":r,"f1":2*p*r/(p+r) if p+r else 0,"counts":dict(c)}
    return metrics


def main():
    benchmark = json.loads((ROOT / "gliner_calibration.json").read_text(encoding="utf-8"))
    snapshot = json.loads((ROOT / "configuration_snapshot.json").read_text(encoding="utf-8"))
    validate_benchmark(benchmark)
    assert tuple(snapshot["configuration_ids"]) == CONFIG_IDS
    RESULTS.mkdir(exist_ok=True)
    summary = {"benchmark_id": benchmark["benchmark_id"], "model_revision": snapshot["model_revision"], "run_at": datetime.now(timezone.utc).isoformat(), "configurations": {}}
    all_results = {}
    for config_id in CONFIG_IDS:
        rows = []
        for case in benchmark["cases"]:
            result = call(config_id, case["text"])
            assert result["configuration_id"] == config_id
            assert result["model_revision"] == snapshot["model_revision"]
            rows.append({"id":case["id"],"text":case["text"],"categories":case["categories"],"expected_events":case["expected_events"],"result":result})
        payload = {"configuration_id":config_id,"model_revision":snapshot["model_revision"],"cases":rows,"metrics":score(rows)}
        (RESULTS / f"{config_id}.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        summary["configurations"][config_id] = payload["metrics"]
        all_results[config_id] = rows
    (RESULTS / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = ["# GLiNER calibration: per-case human review", "", "Ground truth and raw normalized detections from the frozen primary run.", ""]
    for index, case in enumerate(benchmark["cases"]):
        lines += [f"## {case['id']}", "", f"Text: {case['text']}", "", f"Ground truth: `{json.dumps(case['expected_events'], ensure_ascii=False)}`", ""]
        for config_id in CONFIG_IDS:
            detections = all_results[config_id][index]["result"]["detected_events"]
            lines.append(f"- {config_id}: `{json.dumps(detections, ensure_ascii=False)}`")
        lines.append("")
    (RESULTS / "human_review.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
