"""Run the original subject-association strategy comparison."""

import json
import statistics
import urllib.request
from pathlib import Path


HERE = Path(__file__).parent
BENCH = HERE.parent / "gliner_calibration.json"
STRATEGIES = (
    "S1_DETERMINISTIC",
    "S2_TRIGGER_RELATIONS",
    "S3_TRIGGER_RECORD",
    "S4_CONSERVATIVE_HYBRID",
)
URL = "http://localhost:8200/calibration/associate"


def norm(x):
    """Normalize optional text for deterministic comparison."""
    if isinstance(x, str):
        return " ".join(x.casefold().split()).strip(".,;:")
    return None


def canonical_expected(e):
    """Return the canonical expected subject representation."""
    if e["belongs_to_narrator"]:
        return "__narrator__"
    return norm(e["subject_text"])


def call(s, text):
    """Call the association endpoint for one strategy and narrative."""
    body = json.dumps(
        {"strategy_id": s, "text": text},
        ensure_ascii=False,
    ).encode()
    request = urllib.request.Request(
        URL,
        data=body,
        headers={"Content-Type": "application/json"},
    )
    return json.load(urllib.request.urlopen(request, timeout=180))


def pairs(expected, detected):
    """Pair expected and detected events by type."""
    remaining = list(enumerate(detected))
    output = []
    for expected_event in expected:
        hit = next(
            (
                (index, detected_event)
                for index, detected_event in remaining
                if detected_event["event_type"] == expected_event["event_type"]
            ),
            None,
        )
        if hit:
            output.append((expected_event, hit[1]))
            remaining = [item for item in remaining if item[0] != hit[0]]
    return output


def metrics(rows):
    """Aggregate subject, temporal, participant, and latency metrics."""
    conditional = subject_ok = resolved = 0
    third_ok = third_unresolved = false_narrator = 0
    narrator_ok = date_ok = date_resolved = 0
    participant_ok = participant_total = 0
    third = narrator = date_total = 0
    third_all = narrator_all = stage1_true_positive = all_ground_truth = 0
    stage2_latencies = []
    total_latencies = []
    additional_calls = []

    for row in rows:
        expected = row["expected_events"]
        detected = row["result"]["associated_events"]
        matched_pairs = pairs(expected, detected)
        stage1_true_positive += len(matched_pairs)
        all_ground_truth += len(expected)
        third_all += sum(not event["belongs_to_narrator"] for event in expected)
        narrator_all += sum(event["belongs_to_narrator"] for event in expected)

        for expected_event, detected_event in matched_pairs:
            conditional += 1
            target = canonical_expected(expected_event)
            actual = norm(detected_event["subject_text"])
            resolved += detected_event["subject_resolution"] == "RESOLVED"
            subject_ok += actual == target

            if expected_event["belongs_to_narrator"]:
                narrator += 1
                narrator_ok += actual == "__narrator__"
            else:
                third += 1
                third_ok += actual == norm(expected_event["subject_text"])
                third_unresolved += detected_event["subject_resolution"] == "UNRESOLVED"
                false_narrator += actual == "__narrator__"

            if expected_event["date_expression"] is not None:
                date_total += 1
                date_resolved += detected_event["date_expression"] is not None
                date_ok += norm(detected_event["date_expression"]) == norm(
                    expected_event["date_expression"]
                )

            if expected_event["event_type"] == "casamento" and "com " in row["text"].casefold():
                participant_total += 1
                expected_participant = (
                    row["text"].split(" com ", 1)[1].split(" em ", 1)[0].strip(". ")
                )
                participant_ok += any(
                    norm(item) == norm(expected_participant)
                    for item in detected_event["participant_texts"]
                )

        stage2_latencies.append(row["result"]["stage2_latency_ms"])
        total_latencies.append(
            row["result"]["stage1_latency_ms"] + row["result"]["stage2_latency_ms"]
        )
        additional_calls.append(row["result"]["additional_model_calls"])

    return {
        "conditional_subject_accuracy": subject_ok / conditional if conditional else None,
        "subject_coverage": resolved / conditional if conditional else None,
        "end_to_end_subject_accuracy": subject_ok / all_ground_truth if all_ground_truth else None,
        "third_party_identification": third_ok / third if third else None,
        "false_narrator_attribution": false_narrator / third if third else None,
        "unresolved_third_party": third_unresolved / third if third else None,
        "narrator_recall": narrator_ok / narrator if narrator else None,
        "date_accuracy": date_ok / date_total if date_total else None,
        "date_coverage": date_resolved / date_total if date_total else None,
        "participant_accuracy": participant_ok / participant_total if participant_total else None,
        "stage1_event_recall": stage1_true_positive / all_ground_truth if all_ground_truth else None,
        "latency": {
            "stage2_mean": statistics.mean(stage2_latencies),
            "stage2_median": statistics.median(stage2_latencies),
            "stage2_p95": sorted(stage2_latencies)[int(0.95 * (len(stage2_latencies) - 1))],
            "total_mean": statistics.mean(total_latencies),
        },
        "additional_calls_mean": statistics.mean(additional_calls),
    }


def main():
    """Run frozen strategies and write results plus a review artifact."""
    benchmark = json.loads(BENCH.read_text(encoding="utf8"))
    summary = {}
    all_rows = {}

    for strategy in STRATEGIES:
        rows = [
            {**case, "result": call(strategy, case["text"])}
            for case in benchmark["cases"]
        ]
        payload = {"strategy": strategy, "rows": rows, "metrics": metrics(rows)}
        (HERE / f"{strategy}.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf8",
        )
        summary[strategy] = payload["metrics"]
        all_rows[strategy] = rows

    (HERE / "summary.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf8",
    )
    critical = [
        case
        for case in benchmark["cases"]
        if "THIRD_PARTY_SUBJECT" in case["categories"]
        or "MULTIPLE_EVENTS" in case["categories"]
    ]
    lines = ["# Subject association human review", ""]
    for case in critical:
        lines += [
            f"## {case['id']}",
            case["text"],
            f"Ground truth: `{json.dumps(case['expected_events'], ensure_ascii=False)}`",
        ]
        for strategy in STRATEGIES:
            row = next(item for item in all_rows[strategy] if item["id"] == case["id"])
            lines.append(
                f"- {strategy}: "
                f"`{json.dumps(row['result']['associated_events'], ensure_ascii=False)}`"
            )
        lines.append("")

    (HERE / "human_review.md").write_text(
        "\n".join(lines),
        encoding="utf8",
    )
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
