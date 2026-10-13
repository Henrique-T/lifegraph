from metrics import match_events, score_dataset, score_shared_ner, score_subjects, score_temporal, subject_outcome
from adapters import adapt_gemma_events


def event(event_id, kind="casamento", start=0, end=5, role="NARRATOR", subject=None, date="2019"):
    return {"event_id": event_id, "event_type": kind, "trigger": {"text": "x", "start": start, "end": end}, "subject": {"expected_text": subject, "normalized_role": role}, "date_expression": {"text": date, "start": 0, "end": 4}, "normalized_time":{"start":f"{date}-01-01T00:00:00Z","end":f"{date}-12-31T23:59:59.999999Z","precision":"YEAR","uncertainty":False}}


def test_duplicate_same_type_matching_uses_span_not_list_position():
    expected = [event("a", start=0, end=5, date="2010"), event("b", start=20, end=25, date="2019")]
    predicted = [{"event_type":"casamento","trigger":{"start":20,"end":25},"date_expression":"2019"},{"event_type":"casamento","trigger":{"start":0,"end":5},"date_expression":"2010"}]
    pairs, extra = match_events(expected, predicted)
    assert [item[1]["date_expression"] for item in pairs] == ["2010", "2019"] and not extra


def test_unresolved_is_abstention_not_resolved_exact_success():
    expected = event("a", role="UNRESOLVED")
    prediction = {"subject_role":"UNRESOLVED", "subject_text":None}
    metrics = score_subjects([(expected, prediction)])
    assert subject_outcome(expected, prediction) == "CORRECT_ABSTENTION"
    assert metrics["counts"]["resolved"] == 0 and metrics["counts"]["correct_resolved"] == 0


def test_unsafe_narrator_on_unresolved():
    expected = event("a", role="UNRESOLVED")
    prediction = {"subject_role":"NARRATOR", "subject_text":"__NARRATOR__"}
    assert subject_outcome(expected, prediction) == "UNSAFE_RESOLUTION"
    metrics = score_subjects([(expected, prediction)])
    assert metrics["unsafe_resolution_on_ambiguous_rate"] == 1
    assert metrics["false_narrator_attribution_rate"] == 1


def test_false_narrator_and_wrong_resolved_rate():
    expected = event("a", role="THIRD_PARTY", subject="Meu irmão")
    prediction = {"subject_role":"NARRATOR", "subject_text":"__NARRATOR__"}
    metrics = score_subjects([(expected, prediction)])
    assert subject_outcome(expected, prediction) == "FALSE_NARRATOR"
    assert metrics["wrong_resolved_subject_rate"] == 1


def test_temporal_signal_breaks_same_type_tie():
    expected = [event("a", start=0, end=5, date="2010")]
    predicted = [{"event_type":"casamento","trigger":{"start":50,"end":55},"date_expression":"2019"},{"event_type":"casamento","trigger":{"start":50,"end":55},"date_expression":"2010"}]
    pairs, _ = match_events(expected, predicted)
    assert pairs[0][1]["date_expression"] == "2010"


def test_negative_case_predictions_remain_false_positives():
    pairs, extras = match_events([], [{"event_type":"obito"}])
    assert pairs == [] and len(extras) == 1


def test_same_type_without_span_or_date_is_not_matched():
    pairs, extras = match_events([event("a", start=0, end=5, date="2019")], [{"event_type":"casamento","trigger":{"start":20,"end":25},"date_expression":"2018"}])
    assert pairs[0][1] is None and len(extras) == 1


def test_supported_temporal_interval_and_year_are_exact():
    expected = event("a")
    prediction = {"date_expression":{"text":"2019","start":0,"end":4},"normalized_time":expected["normalized_time"]}
    metrics = score_temporal([(expected, prediction)])
    assert metrics["normalized_interval_exact_accuracy"] == 1
    assert metrics["year_accuracy"] == 1


def test_tiny_oracle_dry_run_scores_runner_mechanics():
    expected = event("a")
    expected["participants"] = []
    narrative = {"narrative_id":"dummy_001","categories":["SIMPLE_NARRATOR"],"expected_events":[expected],"evaluation_flags":{"negative_case":False,"reported_speech":False,"incidental_person":False,"coordinated_subject":False},"safety_annotations":{"excluded_subject_texts":[],"coordinated_subject_members":[]}}
    prediction = {"event_type":"casamento","trigger":{"start":0,"end":5},"subject_role":"NARRATOR","subject_text":"__NARRATOR__","date_expression":{"text":"2019","start":0,"end":4},"normalized_time":expected["normalized_time"]}
    result = score_dataset({"narratives":[narrative]}, {"dummy_001":{"events":[prediction]}})
    assert result["event_metrics"]["f1"] == 1
    assert result["end_to_end"]["e2e_core_accuracy"] == 1


def test_gemma_adapter_assigns_repeated_exact_triggers_left_to_right():
    events = adapt_gemma_events("casei em 2001 e casei em 2010.", [{"trigger_text":"casei"},{"trigger_text":"casei"}])
    assert [event["trigger"]["start"] for event in events] == [0, 16]


def test_shared_ner_scores_exact_and_relaxed_spans():
    dataset={"narratives":[{"narrative_id":"x","shared_ner_ground_truth":{"person_spans":[{"start":0,"end":4}],"date_spans":[]}}]}
    result=score_shared_ner(dataset,{"x":{"person_spans":[{"start":0,"end":3}],"date_spans":[]}})
    assert result["person_spans"]["exact"]["f1"] == 0
    assert result["person_spans"]["relaxed_overlap"]["f1"] == 1
