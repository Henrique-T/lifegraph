import importlib.util
from pathlib import Path

MODULE_PATH = Path(__file__).with_name("run_calibration.py")
spec = importlib.util.spec_from_file_location("calibration_runner", MODULE_PATH)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


def result(expected, detected):
    return {"expected_events": expected, "result": {"detected_events": detected, "latency_ms": 10}}


def test_metrics_count_exact_type_matches_and_negative_false_positive():
    expected = {"event_type":"casamento","subject_text":"Meu irmão","belongs_to_narrator":False,"date_expression":"2020"}
    detected = {"event_type":"casamento","subject_text":"Meu irmão","date_expression":"2020"}
    metrics = runner.score([result([expected],[detected]), result([], [{"event_type":"obito"}])])
    assert metrics["counts"] == {"tp":1,"fp":1,"fn":0}
    assert metrics["third_party_subject_identification_rate"] == 1
    assert metrics["negative_case_false_positive_rate"] == 1


def test_metrics_preserve_multiple_event_recall():
    events=[{"event_type":"nascimento","subject_text":None,"belongs_to_narrator":True,"date_expression":"1988"},{"event_type":"casamento","subject_text":None,"belongs_to_narrator":True,"date_expression":"2014"}]
    detected=[{"event_type":"nascimento"},{"event_type":"casamento"}]
    assert runner.score([result(events,detected)])["multi_event_recall"] == 1
