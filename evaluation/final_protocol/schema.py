from __future__ import annotations

from datetime import datetime

EVENT_TYPES = {"nascimento", "casamento", "obito", "natimorto"}
SUBJECT_ROLES = {"NARRATOR", "THIRD_PARTY", "UNRESOLVED"}
PRECISIONS = {"DAY", "YEAR", "UNSUPPORTED"}
REQUIRED_FLAGS = {"reported_speech", "incidental_person", "coordinated_subject", "pro_drop", "ambiguous", "negative_case"}


def validate_dataset(payload: dict) -> None:
    assert payload["schema_version"] == "LIFEGRAPH_FINAL_GT_V1"
    narratives = payload["narratives"]
    assert len(narratives) == 100
    assert len({row["narrative_id"] for row in narratives}) == 100
    for row in narratives:
        assert isinstance(row["text"], str) and row["text"].strip()
        assert isinstance(row["categories"], list) and row["categories"]
        flags = row["evaluation_flags"]
        assert set(flags) == REQUIRED_FLAGS and all(isinstance(value, bool) for value in flags.values())
        assert flags["negative_case"] == (len(row["expected_events"]) == 0)
        annotations = row["safety_annotations"]
        assert set(annotations) == {"excluded_subject_texts", "coordinated_subject_members"}
        for mention in annotations["excluded_subject_texts"] + annotations["coordinated_subject_members"]:
            assert isinstance(mention, str) and mention in row["text"]
        assert flags["coordinated_subject"] == bool(annotations["coordinated_subject_members"])
        ner = row["shared_ner_ground_truth"]
        assert set(ner) == {"person_spans", "date_spans"}
        for span in ner["person_spans"] + ner["date_spans"]:
            assert set(span) == {"text", "start", "end"}
            assert row["text"][span["start"]:span["end"]] == span["text"]
        for event in row["expected_events"]:
            assert event["event_type"] in EVENT_TYPES
            trigger = event["trigger"]
            assert row["text"][trigger["start"]:trigger["end"]] == trigger["text"]
            subject = event["subject"]
            assert subject["normalized_role"] in SUBJECT_ROLES
            if subject["normalized_role"] != "THIRD_PARTY":
                assert subject["expected_text"] is None
            elif subject["expected_text"] is not None:
                assert subject["expected_text"] in row["text"]
            for participant in event["participants"]:
                assert participant in row["text"]
            expression = event["date_expression"]
            if expression["text"] is not None:
                assert row["text"][expression["start"]:expression["end"]] == expression["text"]
            normalized = event["normalized_time"]
            assert normalized["precision"] in PRECISIONS
            if normalized["precision"] in {"DAY", "YEAR"}:
                datetime.fromisoformat(normalized["start"].replace("Z", "+00:00"))
                datetime.fromisoformat(normalized["end"].replace("Z", "+00:00"))
