"""Run the development-only A0/B/C Person-Relation V1 comparison."""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from time import perf_counter

from gliner2 import AutoExtractor

ROOT = Path(__file__).resolve().parents[4]
GLINER_APP = ROOT / "gliner-service"
if str(GLINER_APP) not in sys.path:
    sys.path.insert(0, str(GLINER_APP))

from app.model import MODEL_ID, MODEL_REVISION  # noqa: E402
from app.relation_extraction import (  # noqa: E402
    CONFIGURATION_HASH,
    GENERIC_LABELS,
    SPECIFIC_LABELS,
    extract_relations,
)

BASE_CORPUS = ROOT / "evaluation/extraction/person_relations/v1_adversarial.jsonl"
EXPANSION = ROOT / "evaluation/extraction/person_relations/checkpoint_b_expansion.jsonl"
OUTPUT = Path(__file__).resolve().parent
THRESHOLDS = (0.20, 0.30, 0.40, 0.50, 0.60, 0.70)


def load_cases() -> list[dict]:
    """Load only relation-development artifacts."""

    return [
        json.loads(line)
        for path in (BASE_CORPUS, EXPANSION)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def span_occurrences(case: dict) -> list[dict]:
    """Derive unique expected detector spans from candidate surface evidence."""

    text = case["narrative"]
    offsets: defaultdict[str, int] = defaultdict(int)
    spans: list[dict] = []
    seen: set[tuple[int, int]] = set()
    for candidate in case["expected_relation_candidates"]:
        surface = candidate["relation_surface_text"]
        start = text.casefold().find(surface.casefold(), offsets[surface.casefold()])
        if start < 0:
            continue
        end = start + len(surface)
        # Coordinated endpoint expansion shares one relation-expression span.
        if (start, end) in seen:
            continue
        seen.add((start, end))
        spans.append({"start": start, "end": end, "text": text[start:end]})
        offsets[surface.casefold()] = end
    return spans


def overlap(left: dict, right: dict) -> bool:
    """Return whether two half-open spans overlap."""

    return left["start"] < right["end"] and right["start"] < left["end"]


def match_spans(expected: list[dict], predicted: list[dict]) -> tuple[list[tuple[int, int]], list[int], list[int]]:
    """Greedily match exact spans first, then overlap spans."""

    pairs: list[tuple[int, int]] = []
    used: set[int] = set()
    for expected_index, expected_span in enumerate(expected):
        options = [
            index for index, predicted_span in enumerate(predicted)
            if index not in used
            and predicted_span["start"] == expected_span["start"]
            and predicted_span["end"] == expected_span["end"]
        ]
        if not options:
            options = [
                index for index, predicted_span in enumerate(predicted)
                if index not in used and overlap(expected_span, predicted_span)
            ]
        if options:
            chosen = options[0]
            used.add(chosen)
            pairs.append((expected_index, chosen))
    missing = [index for index in range(len(expected)) if index not in {pair[0] for pair in pairs}]
    extra = [index for index in range(len(predicted)) if index not in used]
    return pairs, missing, extra


def match_candidates(expected: list[dict], predicted: list[dict]) -> tuple[list[tuple[int, int]], list[int], list[int]]:
    """Match candidates by canonical type and exact surface, preserving multiplicity."""

    pairs: list[tuple[int, int]] = []
    used: set[int] = set()
    for expected_index, oracle in enumerate(expected):
        options = [
            index for index, item in enumerate(predicted)
            if index not in used
            and item["relation_type"] == oracle["relation_type"]
            and item["relation_surface_text"].casefold() == oracle["relation_surface_text"].casefold()
        ]
        if options:
            chosen = options[0]
            used.add(chosen)
            pairs.append((expected_index, chosen))
    missing = [index for index in range(len(expected)) if index not in {pair[0] for pair in pairs}]
    extra = [index for index in range(len(predicted)) if index not in used]
    return pairs, missing, extra


def ratio(numerator: int, denominator: int) -> float:
    """Return a rounded zero-safe ratio."""

    return round(numerator / denominator, 6) if denominator else 0.0


def score(rows: list[dict]) -> dict:
    """Compute detector, end-to-end, and explicit safety metrics."""

    detector_tp = detector_fp = detector_fn = exact = 0
    candidate_tp = candidate_fp = candidate_fn = 0
    attribute_correct = Counter()
    matched_total = 0
    endpoint_a_total = endpoint_b_total = 0
    endpoint_a_correct = endpoint_b_correct = both_correct = 0
    wrong_resolved_endpoint = 0
    safe_abstentions = 0
    taxonomy = Counter()
    by_tag: defaultdict[str, Counter] = defaultdict(Counter)

    for row in rows:
        case = row["case"]
        expected_spans = span_occurrences(case)
        detections = row["result"]["detections"]
        span_pairs, missing_spans, extra_spans = match_spans(expected_spans, detections)
        detector_tp += len(span_pairs)
        detector_fn += len(missing_spans)
        detector_fp += len(extra_spans)
        exact += sum(
            expected_spans[e]["start"] == detections[p]["start"]
            and expected_spans[e]["end"] == detections[p]["end"]
            for e, p in span_pairs
        )

        expected = case["expected_relation_candidates"]
        predicted = row["result"]["candidates"]
        pairs, missing, extra = match_candidates(expected, predicted)
        candidate_tp += len(pairs)
        candidate_fn += len(missing)
        candidate_fp += len(extra)
        taxonomy["DETECTION_FALSE_NEGATIVE"] += len(missing_spans)
        taxonomy["DETECTION_FALSE_POSITIVE"] += len(extra_spans)
        for tag in case["tags"]:
            by_tag[tag]["expected"] += len(expected)
            by_tag[tag]["predicted"] += len(predicted)
            by_tag[tag]["matched"] += len(pairs)

        unsafe_persistible_indices: set[int] = set()
        for expected_index, predicted_index in pairs:
            oracle = expected[expected_index]
            item = predicted[predicted_index]
            matched_total += 1
            for field, key in (
                ("relation_type", "relation_type"),
                ("relation_surface_text", "surface"),
                ("polarity", "polarity"),
                ("epistemic_status", "epistemic"),
                ("reporting_mode", "reporting"),
                ("temporal_scope", "temporal"),
            ):
                if str(item[field]).casefold() == str(oracle[field]).casefold():
                    attribute_correct[key] += 1
                elif field == "polarity" and oracle[field] == "NEGATED":
                    taxonomy["NEGATION_LOST"] += 1
                elif field == "epistemic_status" and oracle[field] == "UNCERTAIN":
                    taxonomy["UNCERTAINTY_LOST"] += 1
                elif field == "epistemic_status" and oracle[field] == "HYPOTHETICAL":
                    taxonomy["HYPOTHETICAL_LOST"] += 1
                elif field == "reporting_mode" and oracle[field] == "REPORTED":
                    taxonomy["REPORTED_MODE_LOST"] += 1
                elif field == "temporal_scope":
                    taxonomy["TEMPORAL_SCOPE_WRONG"] += 1

            endpoint_a_total += 1
            endpoint_b_total += 1
            a_match = (item["endpoint_a_mention"] or "").casefold() == (oracle["endpoint_a_mention"] or "").casefold()
            b_match = (item["endpoint_b_mention"] or "").casefold() == (oracle["endpoint_b_mention"] or "").casefold()
            endpoint_a_correct += a_match
            endpoint_b_correct += b_match
            both_correct += a_match and b_match
            if item["endpoint_a_resolution_state"] == "RESOLVED_MENTION" and not a_match:
                wrong_resolved_endpoint += 1
                taxonomy["WRONG_ENDPOINT_A"] += 1
            if item["endpoint_b_resolution_state"] == "RESOLVED_MENTION" and not b_match:
                wrong_resolved_endpoint += 1
                taxonomy["WRONG_ENDPOINT_B"] += 1
            if not a_match and not b_match:
                taxonomy["WRONG_ENDPOINT_PAIR"] += 1
            partial_expected = "partial_endpoint" in case["tags"] or "pronoun" in case["tags"]
            unresolved = "UNRESOLVED_MENTION" in {
                item["endpoint_a_resolution_state"], item["endpoint_b_resolution_state"]
            }
            if partial_expected and unresolved and a_match and b_match:
                safe_abstentions += 1
                taxonomy["SAFE_ENDPOINT_ABSTENTION"] += 1
            if "pronoun" in case["tags"] and not unresolved:
                taxonomy["UNSAFE_PRONOUN_RESOLUTION"] += 1
            if "speaker_distractor" in case["tags"] and item["endpoint_a_mention"] == item.get("reporting_source_mention"):
                taxonomy["REPORTING_SPEAKER_AS_ENDPOINT"] += 1
            eligible = item["persistence_eligibility"] == "LINGUISTICALLY_ELIGIBLE_REVIEW_AND_BINDING_REQUIRED"
            if eligible and (not oracle["persistible_in_v1"] or not a_match or not b_match):
                unsafe_persistible_indices.add(predicted_index)

        for predicted_index in extra:
            item = predicted[predicted_index]
            if item["persistence_eligibility"] == "LINGUISTICALLY_ELIGIBLE_REVIEW_AND_BINDING_REQUIRED":
                unsafe_persistible_indices.add(predicted_index)

        if predicted and not expected:
            tags = set(case["tags"])
            mapping = {
                "question": "QUESTION_FACTUALIZED",
                "quoted_language": "QUOTATION_FACTUALIZED",
                "incidental_kinship": "INCIDENTAL_KINSHIP_FACTUALIZED",
                "metaphor": "METAPHOR_FACTUALIZED",
            }
            for tag, failure in mapping.items():
                if tag in tags:
                    taxonomy[failure] += len(predicted)
        taxonomy["UNSAFE_PERSISTIBLE_FALSE_POSITIVE"] += len(unsafe_persistible_indices)

    detector_precision = ratio(detector_tp, detector_tp + detector_fp)
    detector_recall = ratio(detector_tp, detector_tp + detector_fn)
    candidate_precision = ratio(candidate_tp, candidate_tp + candidate_fp)
    candidate_recall = ratio(candidate_tp, candidate_tp + candidate_fn)
    return {
        "detector": {
            "precision": detector_precision,
            "recall": detector_recall,
            "f1": ratio(2 * detector_precision * detector_recall, detector_precision + detector_recall),
            "exact_span": ratio(exact, detector_tp),
            "overlap_span": ratio(detector_tp, detector_tp + detector_fn),
            "false_positives": detector_fp,
            "false_negatives": detector_fn,
        },
        "end_to_end": {
            "precision": candidate_precision,
            "recall": candidate_recall,
            "f1": ratio(2 * candidate_precision * candidate_recall, candidate_precision + candidate_recall),
            "relation_type_accuracy": ratio(attribute_correct["relation_type"], matched_total),
            "surface_accuracy": ratio(attribute_correct["surface"], matched_total),
            "endpoint_a_accuracy": ratio(endpoint_a_correct, endpoint_a_total),
            "endpoint_b_accuracy": ratio(endpoint_b_correct, endpoint_b_total),
            "both_endpoint_accuracy": ratio(both_correct, matched_total),
            "polarity_accuracy": ratio(attribute_correct["polarity"], matched_total),
            "epistemic_accuracy": ratio(attribute_correct["epistemic"], matched_total),
            "reporting_accuracy": ratio(attribute_correct["reporting"], matched_total),
            "temporal_accuracy": ratio(attribute_correct["temporal"], matched_total),
            "false_relation_candidates": candidate_fp,
            "missed_relation_candidates": candidate_fn,
            "wrong_resolved_endpoint": wrong_resolved_endpoint,
            "safe_abstentions": safe_abstentions,
            "unsafe_persistible_false_positive": taxonomy["UNSAFE_PERSISTIBLE_FALSE_POSITIVE"],
        },
        "failure_taxonomy": dict(sorted(taxonomy.items())),
        "by_phenomenon": {tag: dict(values) for tag, values in sorted(by_tag.items())},
    }


def evaluate(cases: list[dict], strategy: str, threshold: float, raw_outputs: dict[str, dict] | None = None) -> tuple[list[dict], dict]:
    """Evaluate one detector configuration through the shared pipeline."""

    rows = []
    for case in cases:
        raw = raw_outputs.get(case["case_id"]) if raw_outputs else None
        result = extract_relations(
            case["narrative"], case["case_id"], strategy, threshold, raw
        ).model_dump(mode="json")
        rows.append({"case": case, "result": result})
    return rows, score(rows)


def safety_sort(item: tuple[float, dict]) -> tuple:
    """Apply the frozen safety-first strategy selection priority."""

    threshold, metrics = item
    end = metrics["end_to_end"]
    return (
        end["unsafe_persistible_false_positive"],
        end["wrong_resolved_endpoint"],
        end["false_relation_candidates"],
        -end["precision"],
        -end["both_endpoint_accuracy"],
        -end["relation_type_accuracy"],
        -end["recall"],
        -end["f1"],
        -threshold,
    )


def model_outputs(model, cases: list[dict], labels: dict, strategy: str) -> dict[str, dict]:
    """Run one GLiNER label configuration once at the minimum threshold."""

    outputs = {}
    for index, case in enumerate(cases, 1):
        outputs[case["case_id"]] = model.extract_entities(
            case["narrative"], labels, threshold=min(THRESHOLDS),
            include_confidence=True, include_spans=True,
        )
        if index % 10 == 0:
            print(f"{strategy}: {index}/{len(cases)}", flush=True)
    return outputs


def write_json(name: str, value: object) -> None:
    """Write one reproducible development artifact."""

    (OUTPUT / name).write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def main() -> None:
    """Execute A0 and the two GLiNER detector configurations."""

    cases = load_cases()
    started = perf_counter()
    a0_rows, a0_metrics = evaluate(cases, "A0", 1.0)
    print("A0 complete", flush=True)

    model = AutoExtractor.from_pretrained(
        MODEL_ID, revision=MODEL_REVISION, map_location="cpu"
    )
    raw_by_strategy = {
        "B": model_outputs(model, cases, SPECIFIC_LABELS, "B"),
        "C": model_outputs(model, cases, GENERIC_LABELS, "C"),
    }
    sweep: dict[str, list[dict]] = {}
    selected: dict[str, dict] = {"A0": {"threshold": 1.0, "metrics": a0_metrics}}
    prediction_rows: dict[str, list[dict]] = {"A0": a0_rows}
    for strategy in ("B", "C"):
        evaluated = []
        rows_by_threshold = {}
        for threshold in THRESHOLDS:
            rows, metrics = evaluate(cases, strategy, threshold, raw_by_strategy[strategy])
            evaluated.append((threshold, metrics))
            rows_by_threshold[threshold] = rows
        chosen_threshold, chosen_metrics = min(evaluated, key=safety_sort)
        selected[strategy] = {"threshold": chosen_threshold, "metrics": chosen_metrics}
        prediction_rows[strategy] = rows_by_threshold[chosen_threshold]
        sweep[strategy] = [
            {"threshold": threshold, "metrics": metrics}
            for threshold, metrics in evaluated
        ]

    config = {
        "development_only": True,
        "corpus_files": [str(BASE_CORPUS.relative_to(ROOT)), str(EXPANSION.relative_to(ROOT))],
        "narratives": len(cases),
        "expected_candidates": sum(len(case["expected_relation_candidates"]) for case in cases),
        "model_id": MODEL_ID,
        "model_revision": MODEL_REVISION,
        "specific_labels": SPECIFIC_LABELS,
        "generic_labels": GENERIC_LABELS,
        "threshold_grid": THRESHOLDS,
        "configuration_hash": CONFIGURATION_HASH,
        "shared_downstream": True,
    }
    write_json("experiment_config.json", config)
    write_json("threshold_sweep.json", sweep)
    write_json("metrics.json", selected)
    for strategy, rows in prediction_rows.items():
        write_json(f"predictions_{strategy}.json", rows)
    write_json(
        "execution_summary.json",
        {"elapsed_seconds": round(perf_counter() - started, 3), "selected": {
            key: value["threshold"] for key, value in selected.items()
        }},
    )
    print(json.dumps({key: value["metrics"]["end_to_end"] for key, value in selected.items()}, indent=2))


if __name__ == "__main__":
    main()
