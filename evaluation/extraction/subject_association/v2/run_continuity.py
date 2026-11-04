"""Evaluate Portuguese subject continuity strategies."""

import json
import statistics
import time
import urllib.request
from collections import Counter
from pathlib import Path

HERE = Path(__file__).parent
ORIGINAL = HERE.parents[1] / "gliner_calibration.json"
ADVERSARIAL = HERE / "portuguese_continuity_adversarial.json"
URL = "http://localhost:8200/calibration/associate"
STRATEGIES = ("S1_DETERMINISTIC", "S1B_PORTUGUESE_CONTINUITY")


def norm(value):
    """Normalize optional text for deterministic comparison."""
    return " ".join(value.casefold().split()).strip(".,;:!?") if isinstance(value, str) else None


def expected_subject(event):
    """Return the canonical expected subject representation."""
    return "__narrator__" if event["belongs_to_narrator"] else norm(event.get("subject_text"))


def call(strategy, text):
    """Call the association endpoint for one strategy and narrative."""
    body = json.dumps({"strategy_id": strategy, "text": text}, ensure_ascii=False).encode()
    request = urllib.request.Request(URL, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=180) as response:
        return json.load(response)


def pair_events(expected, detected):
    """Pair expected and detected events deterministically."""
    remaining = list(enumerate(detected))
    pairs = []
    for event in expected:
        hit = next(((index, item) for index, item in remaining if item["event_type"] == event["event_type"]), None)
        if hit:
            pairs.append((event, hit[1]))
            remaining = [item for item in remaining if item[0] != hit[0]]
    return pairs


def expected_participants(case, event):
    """Return participant text expected for a benchmark event."""
    if "participant_texts" in event:
        return [norm(item) for item in event["participant_texts"]]
    if event["event_type"] == "casamento" and " com " in case["text"].casefold():
        return [norm(case["text"].split(" com ", 1)[1].split(" em ", 1)[0].strip(". "))]
    return []


def metrics(rows):
    """Aggregate subject, participant, and latency metrics."""
    counts = Counter()
    stage2_latencies = []
    for row in rows:
        expected = row["expected_events"]
        detected = row["result"]["associated_events"]
        pairs = pair_events(expected, detected)
        counts["ground_truth"] += len(expected)
        counts["stage1_matched"] += len(pairs)
        stage2_latencies.append(row["result"]["stage2_latency_ms"])
        for event in expected:
            counts["third_party_all"] += not event["belongs_to_narrator"]
            counts["narrator_all"] += event["belongs_to_narrator"]
            counts["explicit_third_all"] += (not event["belongs_to_narrator"] and event.get("subject_text") is not None)
        for event, candidate in pairs:
            target = expected_subject(event)
            actual = norm(candidate.get("subject_text"))
            counts["conditional"] += 1
            counts["resolved"] += candidate["subject_resolution"] == "RESOLVED"
            counts["subject_correct"] += actual == target
            if event["belongs_to_narrator"]:
                counts["narrator_matched"] += 1
                counts["narrator_correct"] += actual == "__narrator__"
            else:
                counts["third_matched"] += 1
                counts["false_narrator"] += actual == "__narrator__"
                if event.get("subject_text") is not None:
                    counts["explicit_third_matched"] += 1
                    counts["third_correct"] += actual == norm(event["subject_text"])
                counts["third_unresolved"] += candidate["subject_resolution"] == "UNRESOLVED"
            if event.get("date_expression") is not None:
                counts["date_total"] += 1
                counts["date_correct"] += norm(candidate.get("date_expression")) == norm(event["date_expression"])
            expected_parts = expected_participants(row, event)
            if expected_parts:
                counts["participant_total"] += 1
                actual_parts = [norm(item) for item in candidate.get("participant_texts", [])]
                counts["participant_correct"] += all(item in actual_parts for item in expected_parts)
            if actual == target:
                counts["outcome_correct"] += 1
            elif candidate["subject_resolution"] == "UNRESOLVED":
                counts["outcome_safe_abstention"] += 1
            elif not event["belongs_to_narrator"] and actual == "__narrator__":
                counts["outcome_false_narrator"] += 1
            elif not event["belongs_to_narrator"]:
                counts["outcome_wrong_third_party"] += 1
            else:
                counts["outcome_wrong_propagation"] += 1

    ratio = lambda numerator, denominator: counts[numerator] / counts[denominator] if counts[denominator] else None
    return {
        "counts": dict(counts),
        "conditional_subject_exact_accuracy": ratio("subject_correct", "conditional"),
        "subject_resolution_coverage": ratio("resolved", "conditional"),
        "end_to_end_subject_accuracy": ratio("subject_correct", "ground_truth"),
        "end_to_end_third_party_identification": ratio("third_correct", "explicit_third_all"),
        "false_narrator_attribution": ratio("false_narrator", "third_party_all"),
        "narrator_recall": ratio("narrator_correct", "narrator_all"),
        "unresolved_subject_rate": 1 - ratio("resolved", "conditional") if counts["conditional"] else None,
        "date_exact_accuracy": ratio("date_correct", "date_total"),
        "participant_accuracy": ratio("participant_correct", "participant_total"),
        "stage1_event_recall": ratio("stage1_matched", "ground_truth"),
        "stage2_latency_ms": {
            "mean": statistics.mean(stage2_latencies),
            "median": statistics.median(stage2_latencies),
            "p95": sorted(stage2_latencies)[int(0.95 * (len(stage2_latencies) - 1))],
        },
    }


def category_accuracy(rows, category):
    """Compute subject accuracy for one benchmark category."""
    selected = [row for row in rows if category in row["categories"]]
    correct = total = 0
    for row in selected:
        for expected, detected in pair_events(row["expected_events"], row["result"]["associated_events"]):
            total += 1
            correct += norm(detected.get("subject_text")) == expected_subject(expected)
    return {"correct": correct, "total": total, "accuracy": correct / total if total else None}


def cross_sentence_errors(rows):
    """Count unsafe subject propagation across sentence boundaries."""
    selected = [row for row in rows if "SENTENCE_BOUNDARY" in row["categories"]]
    errors = 0
    for row in selected:
        pairs = pair_events(row["expected_events"], row["result"]["associated_events"])
        errors += sum(norm(detected.get("subject_text")) != expected_subject(expected) and detected["subject_resolution"] == "RESOLVED" for expected, detected in pairs[1:])
    return {"errors": errors, "cases": len(selected)}


def run_dataset(path, label):
    """Run all configured strategies against one dataset."""
    benchmark = json.loads(path.read_text(encoding="utf-8"))
    outputs = {}
    for strategy in STRATEGIES:
        rows = []
        for case in benchmark["cases"]:
            result = call(strategy, case["text"])
            rows.append({**case, "result": result})
        payload = {
            "dataset": label,
            "strategy": strategy,
            "rows": rows,
            "metrics": metrics(rows),
            "special_metrics": {
                "pro_drop_narrator": category_accuracy(rows, "PRO_DROP_NARRATOR"),
                "coordinated_subject_continuity": category_accuracy(rows, "COORDINATED_SAME_SUBJECT"),
                "subject_switch": category_accuracy(rows, "COORDINATED_SUBJECT_SWITCH"),
                "cross_sentence_propagation": cross_sentence_errors(rows),
            },
        }
        output_name = ("S1" if strategy == "S1_DETERMINISTIC" else "S1B") + "_" + label.upper() + ".json"
        (HERE / output_name).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        outputs[strategy] = payload
    return outputs


def human_review(datasets):
    """Render selected strategy outputs for manual inspection."""
    lines = ["# S1B Portuguese continuity human review", "", "Every subject newly resolved by S1B compared with frozen S1 is listed below.", ""]
    newly_resolved = []
    for dataset_name, outputs in datasets.items():
        baseline = {row["id"]: row for row in outputs["S1_DETERMINISTIC"]["rows"]}
        for row in outputs["S1B_PORTUGUESE_CONTINUITY"]["rows"]:
            old = baseline[row["id"]]["result"]["associated_events"]
            new = row["result"]["associated_events"]
            expected_pairs = pair_events(row["expected_events"], new)
            for index, (expected, candidate) in enumerate(expected_pairs):
                old_candidate = old[index] if index < len(old) and old[index]["event_type"] == candidate["event_type"] else None
                if old_candidate and old_candidate["subject_resolution"] == "UNRESOLVED" and candidate["subject_resolution"] == "RESOLVED":
                    correct = norm(candidate["subject_text"]) == expected_subject(expected)
                    newly_resolved.append((dataset_name, row, expected, old_candidate, candidate, correct))
    for dataset_name, row, expected, old, new, correct in newly_resolved:
        lines.extend([
            f"## {dataset_name} / {row['id']} / {new['event_type']}",
            f"- Text: {row['text']}",
            f"- Trigger: `{new['trigger_text']}`",
            f"- Expected subject: `{expected_subject(expected)}`",
            f"- S1: `{old.get('subject_text')}` ({old['subject_resolution']})",
            f"- S1B: `{new.get('subject_text')}` ({new['subject_resolution']})",
            f"- Reason: `{new.get('subject_reason')}`",
            f"- Assessment: **{'improvement' if correct else 'regression'}**",
            "",
        ])
    wrong = [item for item in newly_resolved if not item[-1]]
    lines.extend(["# Wrong newly resolved subjects", "", f"Count: {len(wrong)}", ""])
    for dataset_name, row, expected, _, new, _ in wrong:
        lines.append(f"- {dataset_name}/{row['id']}: expected `{expected_subject(expected)}`, got `{new['subject_text']}`.")
    (HERE / "human_review.md").write_text("\n".join(lines), encoding="utf-8")
    return {"total": len(newly_resolved), "correct": len(newly_resolved) - len(wrong), "wrong": len(wrong)}


def main():
    """Run the continuity benchmark and write its artifacts."""
    started = time.time()
    datasets = {
        "original_35": run_dataset(ORIGINAL, "original_35"),
        "adversarial": run_dataset(ADVERSARIAL, "adversarial"),
    }
    review = human_review(datasets)
    summary = {
        "completed_at_epoch": time.time(),
        "duration_seconds": time.time() - started,
        "datasets": {
            name: {strategy: {"metrics": payload["metrics"], "special_metrics": payload["special_metrics"]} for strategy, payload in outputs.items()}
            for name, outputs in datasets.items()
        },
        "newly_resolved_review": review,
    }
    (HERE / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
