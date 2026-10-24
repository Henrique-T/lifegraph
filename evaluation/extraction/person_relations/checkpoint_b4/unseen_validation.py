"""Structural validation of the sealed B.4 development micro-challenge."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

RELATIONS = {"FATHER_OF", "MOTHER_OF", "SON_OF", "DAUGHTER_OF", "BROTHER_OF", "SISTER_OF", "SPOUSE_OF"}
TARGETS = {"EXPLICIT_MENTION", "NARRATOR_ROLE", "UNRESOLVED_MENTION"}


def validate(path: Path):
    raw = path.read_bytes()
    rows = [json.loads(line) for line in raw.decode("utf-8", errors="strict").splitlines() if line.strip()]
    assert len({row["case_id"] for row in rows}) == len(rows)
    for row in rows:
        for item in row["expected_relation_candidates"]:
            assert item["relation_type"] in RELATIONS
            assert item["relation_surface_text"] in row["narrative"]
            assert item["endpoint_a_semantic_target"] in TARGETS
            assert item["endpoint_b_semantic_target"] in TARGETS
            for side in ("a", "b"):
                mention = item[f"endpoint_{side}_mention"]
                if item[f"endpoint_{side}_semantic_target"] != "UNRESOLVED_MENTION":
                    assert mention in row["narrative"]
            if item["interrogative"]:
                assert "?" in row["narrative"]
                assert item["epistemic_status"] == "UNCERTAIN"
                assert not item["persistible_in_v1"]
            eligible = (
                not item["interrogative"] and item["polarity"] == "POSITIVE"
                and item["epistemic_status"] == "ASSERTED" and item["reporting_mode"] == "DIRECT"
                and item["temporal_scope"] == "CURRENT_OR_UNSPECIFIED"
                and item["endpoint_a_semantic_target"] != "UNRESOLVED_MENTION"
                and item["endpoint_b_semantic_target"] != "UNRESOLVED_MENTION"
            )
            assert item["persistible_in_v1"] == eligible
    return rows, hashlib.sha256(raw).hexdigest()


if __name__ == "__main__":
    rows, digest = validate(Path(__file__).with_name("checkpoint_b4_unseen.jsonl"))
    print(json.dumps({"narratives": len(rows), "sha256": digest}, indent=2))
