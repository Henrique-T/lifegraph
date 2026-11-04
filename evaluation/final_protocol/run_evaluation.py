"""Score frozen prediction files. This module never invokes a model or product service."""
import argparse
import json
from pathlib import Path

from adapters import adapt_gemma_events
from metrics import score_dataset, score_shared_ner
from schema import validate_dataset


def valid_event(event):
    """Return whether a predicted event contains required fields."""
    trigger = event.get("trigger")
    return (
        event.get("event_type") in {"nascimento", "casamento", "obito", "natimorto"}
        and isinstance(trigger, dict)
        and isinstance(trigger.get("start"), int)
        and isinstance(trigger.get("end"), int)
        and event.get("subject_role") in {"NARRATOR", "THIRD_PARTY", "UNRESOLVED"}
        and isinstance(event.get("participant_texts"), list)
        and (event.get("date_expression") is None or isinstance(event.get("date_expression"), dict))
        and isinstance(event.get("normalized_time"), dict)
    )


def main():
    """Validate predictions and compute frozen evaluation metrics."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--predictions", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--format", choices=("canonical", "gemma"), default="canonical")
    parser.add_argument("--task", choices=("extraction", "shared_ner"), default="extraction")
    args = parser.parse_args()
    dataset = json.loads(Path(args.dataset).read_text(encoding="utf-8"))
    validate_dataset(dataset)
    prediction_payload = json.loads(Path(args.predictions).read_text(encoding="utf-8"))
    prediction_rows = prediction_payload.get("narratives")
    if not isinstance(prediction_rows, list):
        raise ValueError("MODEL_OUTPUT_INVALID: narratives must be a list")
    predictions = {}
    source_texts = {row["narrative_id"]: row["text"] for row in dataset["narratives"]}
    failures = {"MODEL_OUTPUT_INVALID": 0, "MODEL_TIMEOUT": 0, "MODEL_SERVICE_FAILURE": 0}
    for row in prediction_rows:
        narrative_id = row.get("narrative_id")
        if not narrative_id or narrative_id in predictions:
            raise ValueError("MODEL_OUTPUT_INVALID: missing or duplicate narrative_id")
        failure = row.get("failure")
        if failure:
            if failure not in failures:
                raise ValueError(f"MODEL_OUTPUT_INVALID: unknown failure {failure}")
            failures[failure] += 1
            row = ({"narrative_id": narrative_id, "person_spans": [], "date_spans": []} if args.task == "shared_ner" else {"narrative_id": narrative_id, "events": []})
            predictions[narrative_id] = row
            continue
        if args.task == "shared_ner":
            if not isinstance(row.get("person_spans"), list) or not isinstance(row.get("date_spans"), list):
                failures["MODEL_OUTPUT_INVALID"] += 1
                row = {"narrative_id":narrative_id,"person_spans":[],"date_spans":[]}
            predictions[narrative_id] = row
            continue
        if not isinstance(row.get("events"), list):
            raise ValueError(f"MODEL_OUTPUT_INVALID: events must be a list for {narrative_id}")
        if args.format == "gemma":
            try:
                row["events"] = adapt_gemma_events(source_texts.get(narrative_id, ""), row["events"])
            except ValueError:
                failures["MODEL_OUTPUT_INVALID"] += 1
                row = {"narrative_id": narrative_id, "events": []}
        if row["events"] and not all(valid_event(event) for event in row["events"]):
            failures["MODEL_OUTPUT_INVALID"] += 1
            row = {"narrative_id": narrative_id, "events": []}
        predictions[narrative_id] = row
    expected_ids = {row["narrative_id"] for row in dataset["narratives"]}
    if set(predictions) != expected_ids:
        raise ValueError("MODEL_OUTPUT_INVALID: prediction narrative IDs do not match the frozen dataset")
    result = {"metrics": score_shared_ner(dataset,predictions) if args.task == "shared_ner" else score_dataset(dataset, predictions), "model_failures": failures, "task":args.task}
    Path(args.output).write_text(json.dumps(result, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
