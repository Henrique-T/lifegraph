"""B.4 artifact and metric semantics tests."""

import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent


def module(name):
    spec = importlib.util.spec_from_file_location(name, HERE / name)
    assert spec and spec.loader
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


def test_micro_challenge_is_valid_and_balanced():
    rows, digest = module("unseen_validation.py").validate(HERE / "checkpoint_b4_unseen.jsonl")
    assert 20 <= len(rows) <= 30
    assert len(digest) == 64
    assert sum(not row["expected_relation_candidates"] for row in rows) >= 5
    candidates = [item for row in rows for item in row["expected_relation_candidates"]]
    assert sum(item["persistible_in_v1"] for item in candidates) >= 5
    assert sum(not item["persistible_in_v1"] for item in candidates) >= 5
    assert len({item["relation_type"] for item in candidates}) == 7


def test_all_question_candidates_are_blocked_by_oracle():
    rows, _ = module("unseen_validation.py").validate(HERE / "checkpoint_b4_unseen.jsonl")
    questions = [item for row in rows for item in row["expected_relation_candidates"] if item["interrogative"]]
    assert questions
    assert all(not item["persistible_in_v1"] for item in questions)


def test_metric_names_separate_candidate_from_unsafe_fact():
    source = (HERE / "run.py").read_text(encoding="utf-8")
    assert "QUESTION_RELATION_CANDIDATE" in source
    assert "QUESTION_CORRECTLY_BLOCKED" in source
    assert "QUESTION_UNSAFE_PERSISTIBLE" in source
