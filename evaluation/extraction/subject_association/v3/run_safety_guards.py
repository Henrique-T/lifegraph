"""Evaluate conservative subject-association safety guards."""

import json
import re
import statistics
import time
import urllib.request
from collections import Counter
from pathlib import Path

HERE = Path(__file__).parent
EXTRACTION = HERE.parents[1]
DATASETS = {
    "ORIGINAL": EXTRACTION / "gliner_calibration.json",
    "V2": EXTRACTION / "subject_association" / "v2" / "portuguese_continuity_adversarial.json",
    "V3": HERE / "safety_guards_adversarial.json",
}
STRATEGIES = ("S1_DETERMINISTIC", "S1B_PORTUGUESE_CONTINUITY", "S1C_CONSERVATIVE_GUARDS")
URL = "http://localhost:8200/calibration/associate"
REPORTING = re.compile(r"^(.+?)\s+(?:disse|contou|afirmou|falou|declarou)\b", re.I)
INCIDENTAL = re.compile(r"\b(?:com|para|sobre)\s+([A-ZÁÉÍÓÚÂÊÔÃÕÇ][\wÀ-ÿ'-]*(?:\s+[A-ZÁÉÍÓÚÂÊÔÃÕÇ][\wÀ-ÿ'-]*)*)", re.I)


def norm(value):
    """Normalize optional text for deterministic comparison."""
    return " ".join(value.casefold().split()).strip(".,;:!?") if isinstance(value, str) else None


def target(event):
    """Return the canonical expected subject representation."""
    return "__narrator__" if event["belongs_to_narrator"] else norm(event.get("subject_text"))


def call(strategy, text):
    """Call the association endpoint for one strategy and narrative."""
    body = json.dumps({"strategy_id": strategy, "text": text}, ensure_ascii=False).encode()
    request = urllib.request.Request(URL, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=180) as response:
        return json.load(response)


def pairs(expected, detected):
    """Pair expected and detected events deterministically."""
    remaining = list(enumerate(detected)); matched = []
    for event in expected:
        hit = next(((index, item) for index, item in remaining if item["event_type"] == event["event_type"]), None)
        if hit:
            matched.append((event, hit[1])); remaining = [item for item in remaining if item[0] != hit[0]]
        else:
            matched.append((event, None))
    return matched


def classify(event, candidate):
    """Classify one subject-association outcome."""
    if candidate is None:
        return "STAGE1_MISS"
    actual = norm(candidate.get("subject_text")); expected = target(event)
    if candidate["subject_resolution"] == "UNRESOLVED":
        return "SAFE_ABSTENTION"
    if actual == expected:
        return "CORRECT_RESOLUTION"
    if not event["belongs_to_narrator"] and actual == "__narrator__":
        return "FALSE_NARRATOR_ATTRIBUTION"
    if event.get("coordinated_subject"):
        return "COORDINATED_SUBJECT_UNSAFE"
    if expected and actual and actual in expected and actual != expected:
        return "TRUNCATED_SUBJECT"
    if candidate.get("subject_reason") == "COORDINATED_SUBJECT_CONTINUITY":
        return "WRONG_SUBJECT_PROPAGATION"
    return "WRONG_THIRD_PARTY_SUBJECT"


def metrics(rows):
    """Aggregate general subject-association metrics."""
    c = Counter(); latencies = []
    for row in rows:
        event_pairs = pairs(row["expected_events"], row["result"]["associated_events"])
        latencies.append(row["result"]["stage2_latency_ms"])
        for event, candidate in event_pairs:
            c["ground_truth"] += 1
            taxonomy = classify(event, candidate); c[taxonomy] += 1
            c["third_party"] += not event["belongs_to_narrator"]
            c["narrator"] += event["belongs_to_narrator"]
            if candidate is None:
                continue
            c["detected"] += 1
            resolved = candidate["subject_resolution"] == "RESOLVED"
            c["resolved"] += resolved
            correct = resolved and norm(candidate.get("subject_text")) == target(event)
            c["subject_correct"] += correct
            c["wrong_resolved"] += resolved and not correct
            c["false_narrator"] += (not event["belongs_to_narrator"] and norm(candidate.get("subject_text")) == "__narrator__")
            c["third_correct"] += (not event["belongs_to_narrator"] and correct)
            c["narrator_correct"] += (event["belongs_to_narrator"] and correct)
            if event.get("date_expression") is not None:
                c["date_total"] += 1; c["date_correct"] += norm(candidate.get("date_expression")) == norm(event["date_expression"])
            expected_parts = [norm(item) for item in event.get("participant_texts", [])]
            if expected_parts:
                c["participant_total"] += 1
                actual_parts = [norm(item) for item in candidate.get("participant_texts", [])]
                c["participant_correct"] += all(item in actual_parts for item in expected_parts)
    ratio = lambda a, b: c[a] / c[b] if c[b] else None
    return {
        "counts": dict(c),
        "subject_exact_accuracy": ratio("subject_correct", "ground_truth"),
        "subject_coverage": ratio("resolved", "detected"),
        "wrong_resolved_subject_rate": ratio("wrong_resolved", "resolved"),
        "false_narrator_attribution": ratio("false_narrator", "third_party"),
        "third_party_identification": ratio("third_correct", "third_party"),
        "narrator_recall": ratio("narrator_correct", "narrator"),
        "date_exact_accuracy": ratio("date_correct", "date_total"),
        "participant_accuracy": ratio("participant_correct", "participant_total"),
        "stage1_recall": ratio("detected", "ground_truth"),
        "stage2_latency_ms": {
            "mean": statistics.mean(latencies), "median": statistics.median(latencies),
            "p95": sorted(latencies)[int(.95 * (len(latencies) - 1))],
        },
    }


def v3_safety_metrics(rows):
    """Aggregate safety metrics specific to the adversarial dataset."""
    c = Counter()
    for row in rows:
        categories = set(row["categories"])
        reporting_match = REPORTING.search(row["text"])
        reporting_subject = norm(reporting_match.group(1)) if reporting_match else None
        incidental_people = {norm(value) for value in INCIDENTAL.findall(row["text"])}
        for event, candidate in pairs(row["expected_events"], row["result"]["associated_events"]):
            actual = norm(candidate.get("subject_text")) if candidate else None
            if "REPORTED_SPEECH" in categories:
                c["reported_total"] += 1; c["reported_correct"] += actual == target(event); c["reporter_leak"] += actual == reporting_subject and actual != target(event)
            if "INCIDENTAL_PERSON" in categories:
                c["incidental_total"] += 1; c["incidental_leak"] += actual in incidental_people and actual != target(event)
            if "TRUNCATED_KINSHIP" in categories:
                c["kinship_total"] += 1; c["kinship_exact"] += actual == target(event)
            if event.get("coordinated_subject"):
                c["coordinated_total"] += 1
                c["coordinated_abstained"] += bool(candidate and candidate["subject_resolution"] == "UNRESOLVED")
                c["coordinated_correct"] += actual == target(event)
                c["coordinated_unsafe"] += bool(candidate and candidate["subject_resolution"] == "RESOLVED" and actual != target(event))
    ratio = lambda a, b: c[a] / c[b] if c[b] else None
    return {
        "counts": dict(c),
        "reported_speech_accuracy": ratio("reported_correct", "reported_total"),
        "reporting_person_leakage_rate": ratio("reporter_leak", "reported_total"),
        "incidental_person_leakage_rate": ratio("incidental_leak", "incidental_total"),
        "kinship_subject_exact_accuracy": ratio("kinship_exact", "kinship_total"),
        "coordinated_abstention_rate": ratio("coordinated_abstained", "coordinated_total"),
        "coordinated_unsafe_rate": ratio("coordinated_unsafe", "coordinated_total"),
    }


def run_dataset(name, path):
    """Run configured strategies against one named dataset."""
    benchmark = json.loads(path.read_text(encoding="utf-8")); outputs = {}
    for strategy in STRATEGIES:
        rows = [{**case, "result": call(strategy, case["text"])} for case in benchmark["cases"]]
        payload = {"dataset": name, "strategy": strategy, "rows": rows, "metrics": metrics(rows)}
        if name == "V3": payload["safety_metrics"] = v3_safety_metrics(rows)
        (HERE / f"{strategy.split('_', 1)[0]}_{name}.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        outputs[strategy] = payload
    return outputs


def render_case(lines, section, dataset, row_b, row_c):
    """Append one comparison case to the review document."""
    lines.extend([f"## {section}: {dataset}/{row_c['id']}", f"- Source: {row_c['text']}"])
    for (expected, before), (_, after) in zip(pairs(row_b["expected_events"], row_b["result"]["associated_events"]), pairs(row_c["expected_events"], row_c["result"]["associated_events"])):
        lines.extend([
            f"- Trigger: `{after.get('trigger_text') if after else None}`; expected: `{target(expected)}`",
            f"- S1B: `{before.get('subject_text') if before else None}` / `{before.get('subject_resolution') if before else 'STAGE1_MISS'}`",
            f"- S1C: `{after.get('subject_text') if after else None}` / `{after.get('subject_resolution') if after else 'STAGE1_MISS'}` / `{after.get('subject_reason') if after else None}`",
            f"- Classification: `{classify(expected, after)}`",
        ])
    lines.append("")


def human_review(all_outputs):
    """Render selected safety cases for manual inspection."""
    lines = ["# S1C safety-guard human review", ""]
    emitted = set()
    for dataset, outputs in all_outputs.items():
        b_rows = {row["id"]: row for row in outputs["S1B_PORTUGUESE_CONTINUITY"]["rows"]}
        for row_c in outputs["S1C_CONSERVATIVE_GUARDS"]["rows"]:
            row_b = b_rows[row_c["id"]]; before = pairs(row_b["expected_events"], row_b["result"]["associated_events"]); after = pairs(row_c["expected_events"], row_c["result"]["associated_events"])
            changed = any((b and c and (b.get("subject_text"), b.get("subject_resolution")) != (c.get("subject_text"), c.get("subject_resolution"))) for (_, b), (_, c) in zip(before, after))
            wrong_before = any(classify(e, b) not in ("CORRECT_RESOLUTION", "SAFE_ABSTENTION", "STAGE1_MISS") for e, b in before)
            newly_abstained = any(b and c and b["subject_resolution"] == "RESOLVED" and c["subject_resolution"] == "UNRESOLVED" for (_, b), (_, c) in zip(before, after))
            newly_resolved = any(b and c and b["subject_resolution"] == "UNRESOLVED" and c["subject_resolution"] == "RESOLVED" for (_, b), (_, c) in zip(before, after))
            regression = any(classify(e, c) not in ("CORRECT_RESOLUTION", "SAFE_ABSTENTION", "STAGE1_MISS") and classify(e, b) in ("CORRECT_RESOLUTION", "SAFE_ABSTENTION") for (e, b), (_, c) in zip(before, after))
            sections = []
            if wrong_before and changed: sections.append("A_S1B_WRONG_CHANGED")
            if newly_abstained: sections.append("B_NEWLY_ABSTAINED")
            if newly_resolved: sections.append("C_NEWLY_RESOLVED")
            if regression: sections.append("D_REGRESSION")
            if dataset == "V3":
                for category, section in (("REPORTED_SPEECH", "E_REPORTED_SPEECH"), ("INCIDENTAL_PERSON", "F_INCIDENTAL_PERSON"), ("COORDINATED_HUMAN_SUBJECT", "G_COORDINATED_SUBJECT")):
                    if category in row_c["categories"]: sections.append(section)
            for section in sections:
                key = (section, dataset, row_c["id"])
                if key not in emitted: render_case(lines, section, dataset, row_b, row_c); emitted.add(key)
    (HERE / "human_review.md").write_text("\n".join(lines), encoding="utf-8")


def main():
    """Run safety benchmarks and write result artifacts."""
    started = time.time(); outputs = {name: run_dataset(name, path) for name, path in DATASETS.items()}; human_review(outputs)
    summary = {
        "duration_seconds": time.time() - started,
        "datasets": {name: {strategy: {key: value for key, value in payload.items() if key in ("metrics", "safety_metrics")} for strategy, payload in strategies.items()} for name, strategies in outputs.items()},
    }
    (HERE / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__": main()
