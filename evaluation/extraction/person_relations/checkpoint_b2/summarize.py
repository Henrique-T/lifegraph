"""Create concise Checkpoint B.2 comparison and selection artifacts."""

from __future__ import annotations

import json
from pathlib import Path


HERE = Path(__file__).resolve().parent


def read(name: str):
    """Read one JSON artifact."""
    return json.loads((HERE / name).read_text(encoding="utf-8"))


def write(name: str, value: object) -> None:
    """Write one JSON artifact."""
    (HERE / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    """Materialize safety, abstention, phenomena, and final selection summaries."""
    metrics = read("metrics_all.json")
    safety = {}
    abstention = {}
    phenomena = {}
    for strategy, value in metrics.items():
        safety[strategy] = {}
        abstention[strategy] = {}
        phenomena[strategy] = {}
        for split in ("tuning", "challenge", "combined"):
            item = value[split]
            end, coverage, taxonomy = item["end_to_end"], item["coverage"], item["failure_taxonomy"]
            safety[strategy][split] = {
                "wrong_resolved_endpoint": end["wrong_resolved_endpoint"],
                "unsafe_persistible_false_positive": end["unsafe_persistible_false_positive"],
                "reporting_speaker_as_endpoint": taxonomy.get("REPORTING_SPEAKER_AS_ENDPOINT", 0),
                "distractor_as_endpoint": taxonomy.get("DISTRACTOR_AS_ENDPOINT", 0),
                "unsafe_pronoun_resolution": taxonomy.get("UNSAFE_PRONOUN_RESOLUTION", 0),
                "negation_lost": taxonomy.get("NEGATION_LOST", 0),
                "uncertainty_lost": taxonomy.get("UNCERTAINTY_LOST", 0),
                "hypothetical_lost": taxonomy.get("HYPOTHETICAL_LOST", 0),
                "reported_mode_lost": taxonomy.get("REPORTED_MODE_LOST", 0),
                "temporal_scope_wrong": taxonomy.get("TEMPORAL_SCOPE_WRONG", 0),
                "question_factualized": taxonomy.get("QUESTION_FACTUALIZED", 0),
                "quotation_factualized": taxonomy.get("QUOTATION_FACTUALIZED", 0),
                "incidental_kinship_factualized": taxonomy.get("INCIDENTAL_KINSHIP_FACTUALIZED", 0),
                "metaphor_factualized": taxonomy.get("METAPHOR_FACTUALIZED", 0),
            }
            abstention[strategy][split] = {
                "safe_count": coverage["safe_abstention_count"],
                "safe_rate": coverage["safe_abstention_rate"],
                "unnecessary_count": coverage["unnecessary_abstention_count"],
                "unnecessary_rate": coverage["unnecessary_abstention_rate"],
                "total_miss_count": coverage["total_detector_candidate_miss"],
            }
            phenomena[strategy][split] = coverage["per_phenomenon_recall"]
    selection = {
        "historical_checkpoint_b": "B_SELECTED_BY_ORIGINAL_CHECKPOINT_B_ORDER",
        "checkpoint_b1": "NO_STRATEGY_PASSES_COVERAGE_GATE",
        "checkpoint_b2": "A0_B2",
        "basis": [
            "A0_B2 passes both hard safety gates on tuning, challenge, and combined development data",
            "A0_B2 passes all three R4 coverage components on tuning, challenge, and combined development data",
            "B_B2, C_B2, and D1 fail R4 coverage",
            "No detector was integrated into application behavior",
        ],
        "production_selection": "A0_B2",
        "integration_performed": False,
    }
    write("safety_failures.json", safety)
    write("abstention_analysis.json", abstention)
    write("per_phenomenon_metrics.json", phenomena)
    write("strategy_selection.json", selection)


if __name__ == "__main__":
    main()
