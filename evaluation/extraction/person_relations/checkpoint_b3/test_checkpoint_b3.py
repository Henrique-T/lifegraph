"""Reproducibility and integrity tests for the B.3 freeze evaluation."""

import importlib.util
from pathlib import Path


HERE = Path(__file__).resolve().parent


def load_validator():
    spec = importlib.util.spec_from_file_location("b3_validation", HERE / "unseen_validation.py")
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_unseen_corpus_is_structurally_valid():
    rows, digest = load_validator().load_and_validate(HERE / "checkpoint_b3_unseen.jsonl")
    assert len(rows) == 50
    assert len(digest) == 64


def test_unseen_corpus_covers_every_relation_type_multiple_times():
    rows, _ = load_validator().load_and_validate(HERE / "checkpoint_b3_unseen.jsonl")
    counts = {relation: 0 for relation in load_validator().RELATIONS}
    for row in rows:
        for item in row["expected_relation_candidates"]:
            counts[item["relation_type"]] += 1
    assert min(counts.values()) >= 3


def test_unseen_corpus_has_controls_and_narrator_targets():
    rows, _ = load_validator().load_and_validate(HERE / "checkpoint_b3_unseen.jsonl")
    assert sum(not row["expected_relation_candidates"] for row in rows) >= 15
    targets = [
        item[f"endpoint_{side}_semantic_target"]
        for row in rows for item in row["expected_relation_candidates"] for side in ("a", "b")
    ]
    assert "NARRATOR_ROLE" in targets
    assert "UNRESOLVED_MENTION" in targets
