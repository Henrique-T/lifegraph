"""Unit tests for frozen prediction-runner mechanics without model inference."""

import json
from datetime import datetime, timezone
from types import SimpleNamespace

from generate_predictions import (
    approved_result_to_events,
    atomic_write_json,
    infer_b,
    next_exact_span,
    percentile_95,
)


def test_exact_span_assignment_is_left_to_right_without_fuzzy_repair():
    """Repeated exact substrings consume successive source occurrences."""
    used = set()
    text = "casei em 2001 e casei em 2010"
    assert next_exact_span(text, "casei", used)["start"] == 0
    assert next_exact_span(text, "casei", used)["start"] == 16
    assert next_exact_span(text, "Casei", used) is None


def test_approved_pipeline_mapping_preserves_authoritative_semantics():
    """Production candidates map to the frozen canonical prediction shape."""
    normalized = SimpleNamespace(
        start=datetime(2019, 1, 1, tzinfo=timezone.utc),
        end=datetime(2019, 12, 31, 23, 59, 59, 999999, tzinfo=timezone.utc),
        temporal_precision="YEAR",
    )
    candidates = [
        SimpleNamespace(
            event_type="casamento",
            trigger_text="casei",
            trigger_start=0,
            trigger_end=5,
            subject_text="__NARRATOR__",
            subject_resolution="RESOLVED",
            participant_texts=[],
            date_expression="2019",
            normalized_time_candidate=normalized,
        ),
        SimpleNamespace(
            event_type="obito",
            trigger_text="morreu",
            trigger_start=17,
            trigger_end=23,
            subject_text=None,
            subject_resolution="UNRESOLVED",
            participant_texts=[],
            date_expression=None,
            normalized_time_candidate=None,
        ),
    ]
    events = approved_result_to_events("casei em 2019 e morreu", SimpleNamespace(candidates=candidates))
    assert events[0]["subject_role"] == "NARRATOR"
    assert events[0]["normalized_time"]["start"] == "2019-01-01T00:00:00Z"
    assert events[0]["date_expression"] == {"text": "2019", "start": 9, "end": 13}
    assert events[1]["subject_role"] == "UNRESOLVED"
    assert events[1]["normalized_time"] == {
        "start": None,
        "end": None,
        "precision": "UNSUPPORTED",
        "uncertainty": False,
    }


def test_shared_ner_mapping_filters_labels_and_deduplicates_by_best_score():
    """The B baseline retains exact Pessoa/Data offsets and no other groups."""
    class FakePipeline:
        def __call__(self, text):
            assert text == "Ana nasceu em 2019."
            return [
                {"entity_group": "Pessoa", "start": 0, "end": 3, "score": 0.8},
                {"entity_group": "Pessoa", "start": 0, "end": 3, "score": 0.9},
                {"entity_group": "Data", "start": 14, "end": 18, "score": 0.7},
                {"entity_group": "Local", "start": 4, "end": 10, "score": 0.99},
            ]

    config = {"system_b": {"evaluation_label_map": {"Pessoa": "PERSON", "Data": "DATE"}}}
    result = infer_b(FakePipeline(), "Ana nasceu em 2019.", config)
    assert result["person_spans"] == [{"text": "Ana", "start": 0, "end": 3, "score": 0.9}]
    assert result["date_spans"] == [{"text": "2019", "start": 14, "end": 18, "score": 0.7}]


def test_atomic_output_and_nearest_rank_p95(tmp_path):
    """Results never remain as plausible partial JSON files."""
    output = tmp_path / "result.json"
    atomic_write_json(output, {"ok": True})
    assert json.loads(output.read_text(encoding="utf-8")) == {"ok": True}
    assert not (tmp_path / "result.json.tmp").exists()
    assert percentile_95(list(range(1, 101))) == 95
