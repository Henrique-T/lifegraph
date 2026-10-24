"""Materialize auditable per-case failure and abstention classifications."""

import json
from pathlib import Path

from run import match_candidates

HERE = Path(__file__).resolve().parent


def main() -> None:
    """Classify selected-strategy predictions without rerunning inference."""

    output = {}
    for strategy in ("A0", "B", "C"):
        rows = json.loads((HERE / f"predictions_{strategy}.json").read_text(encoding="utf-8"))
        failures = []
        abstentions = []
        for row in rows:
            case = row["case"]
            expected = case["expected_relation_candidates"]
            predicted = row["result"]["candidates"]
            pairs, missing, extra = match_candidates(expected, predicted)
            if missing:
                failures.append({"case_id": case["case_id"], "category": "DETECTION_FALSE_NEGATIVE", "count": len(missing)})
            if extra:
                failures.append({"case_id": case["case_id"], "category": "RELATION_CANDIDATE_FALSE_POSITIVE", "count": len(extra)})
            for expected_index, predicted_index in pairs:
                oracle = expected[expected_index]
                item = predicted[predicted_index]
                for field, category in (
                    ("endpoint_a_mention", "WRONG_ENDPOINT_A"),
                    ("endpoint_b_mention", "WRONG_ENDPOINT_B"),
                    ("polarity", "NEGATION_LOST"),
                    ("epistemic_status", "EPISTEMIC_STATUS_WRONG"),
                    ("reporting_mode", "REPORTED_MODE_LOST"),
                    ("temporal_scope", "TEMPORAL_SCOPE_WRONG"),
                ):
                    if str(item.get(field) or "").casefold() != str(oracle.get(field) or "").casefold():
                        failures.append({"case_id": case["case_id"], "category": category, "field": field})
                if "UNRESOLVED_MENTION" in {
                    item["endpoint_a_resolution_state"], item["endpoint_b_resolution_state"]
                }:
                    abstentions.append({
                        "case_id": case["case_id"],
                        "endpoint_a": item["endpoint_a_mention"],
                        "endpoint_b": item["endpoint_b_mention"],
                    })
        output[strategy] = {"failures": failures, "abstentions": abstentions}
    (HERE / "failure_cases.json").write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
