"""Structural validation for the development-only B.3 unseen corpus."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

RELATIONS = {"FATHER_OF", "MOTHER_OF", "SON_OF", "DAUGHTER_OF", "BROTHER_OF", "SISTER_OF", "SPOUSE_OF"}
TARGETS = {"EXPLICIT_MENTION", "NARRATOR_ROLE", "UNRESOLVED_MENTION"}
POLARITIES = {"POSITIVE", "NEGATED"}
EPISTEMIC = {"ASSERTED", "UNCERTAIN", "HYPOTHETICAL"}
REPORTING = {"DIRECT", "REPORTED"}
TEMPORAL = {"CURRENT_OR_UNSPECIFIED", "PAST", "UNRESOLVED"}


def load_and_validate(path: Path) -> tuple[list[dict], str]:
    """Validate only oracle structure, never execute extraction."""
    raw = path.read_bytes()
    text = raw.decode("utf-8", errors="strict")
    rows = [json.loads(line) for line in text.splitlines() if line.strip()]
    ids = [row["case_id"] for row in rows]
    assert len(ids) == len(set(ids))
    for row in rows:
        source = row["narrative"]
        assert row["tags"]
        for item in row["expected_relation_candidates"]:
            assert item["relation_type"] in RELATIONS
            assert item["polarity"] in POLARITIES
            assert item["epistemic_status"] in EPISTEMIC
            assert item["reporting_mode"] in REPORTING
            assert item["temporal_scope"] in TEMPORAL
            assert item["endpoint_a_semantic_target"] in TARGETS
            assert item["endpoint_b_semantic_target"] in TARGETS
            surface = item["relation_surface_text"]
            assert surface in source
            for side in ("a", "b"):
                mention = item[f"endpoint_{side}_mention"]
                target = item[f"endpoint_{side}_semantic_target"]
                if target != "UNRESOLVED_MENTION":
                    assert mention and mention in source
            linguistically_eligible = (
                item["polarity"] == "POSITIVE"
                and item["epistemic_status"] == "ASSERTED"
                and item["reporting_mode"] == "DIRECT"
                and item["temporal_scope"] == "CURRENT_OR_UNSPECIFIED"
                and item["endpoint_a_semantic_target"] != "UNRESOLVED_MENTION"
                and item["endpoint_b_semantic_target"] != "UNRESOLVED_MENTION"
            )
            assert item["persistible_in_v1"] == linguistically_eligible
    return rows, hashlib.sha256(raw).hexdigest()


if __name__ == "__main__":
    path = Path(__file__).with_name("checkpoint_b3_unseen.jsonl")
    rows, digest = load_and_validate(path)
    print(json.dumps({"cases": len(rows), "sha256": digest}, indent=2))
