from app.model import map_raw_output, normalize_year


def test_maps_allowed_event_and_preserves_model_metadata() -> None:
    text = "Eu me casei com Ana em 2019."
    raw = {
        "entities": {
            "marriage_event": [
                {"text": "me casei", "start": 3, "end": 11, "confidence": 0.81}
            ],
            "person": [
                {"text": "Ana", "start": 16, "end": 19, "confidence": 0.92}
            ],
            "date": [
                {"text": "2019", "start": 23, "end": 27, "confidence": 0.99}
            ],
        }
    }
    result = map_raw_output(text, raw, 12.0)
    candidate = result.extracted_events[0]
    assert candidate.event_type == "casamento"
    assert candidate.confidence == 0.81
    assert candidate.person_mentions[0].text == "Ana"
    assert candidate.temporal_expression == "2019"
    assert candidate.normalized_time_candidate.temporal_precision == "YEAR"
    assert candidate.uncertainty_detected is None


def test_unknown_event_label_is_ignored() -> None:
    result = map_raw_output(
        "texto",
        {
            "entities": {
                "divorce_event": [
                    {"text": "texto", "start": 0, "end": 5, "confidence": 0.9}
                ]
            }
        },
        1.0,
    )
    assert result.extracted_events == []


def test_negative_empty_model_output_has_no_event() -> None:
    result = map_raw_output("Fui ao supermercado em 2019.", {"entities": {}}, 1.0)
    assert result.extracted_events == []


def test_only_plain_year_is_deterministically_normalized() -> None:
    assert normalize_year("2019").temporal_precision == "YEAR"
    assert normalize_year("por volta de 2019") is None
    assert normalize_year("março de 2019") is None
