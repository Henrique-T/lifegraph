import pytest
from pydantic import ValidationError

from app.calibration import CONFIGURATIONS, _entity_events, _record_events
from app.schemas import CalibrationRequest


def test_registry_is_fixed_and_complete():
    assert tuple(CONFIGURATIONS) == ("A_ENTITY_EVENT_BASELINE", "B_LINGUISTIC_EVENT_SPANS", "C_STRUCTURED_RECORDS", "D_CONSTRAINED_RECORDS", "E_RELATION_EXTRACTION")
    with pytest.raises(TypeError):
        CONFIGURATIONS["X"] = object()


def test_unknown_configuration_and_arbitrary_schema_rejected():
    with pytest.raises(ValidationError):
        CalibrationRequest(text="texto", configuration_id="USER_SCHEMA")
    with pytest.raises(ValidationError):
        CalibrationRequest(text="texto", configuration_id="A_ENTITY_EVENT_BASELINE", schema={"evil":"prompt"})


def test_entity_normalization_keeps_multiple_events():
    raw={"entities":{"birth_expression":[{"text":"nasci","confidence":.8}],"marriage_expression":[{"text":"casei","confidence":.7}],"person":[],"date":[]}}
    result=_entity_events(raw,{"birth_expression":"nascimento","marriage_expression":"casamento"},"B")
    assert [x["event_type"] for x in result] == ["nascimento","casamento"]


def test_record_normalization_rejects_unknown_event_type_and_preserves_subject():
    raw={"civil_event":[{"event_type":"casamento","subject_text":"Meu irmão"},{"event_type":"divorcio","subject_text":"Eu"}]}
    result=_record_events(raw,"C")
    assert result == [{"event_type":"casamento","subject_text":"Meu irmão","participant_texts":[],"date_expression":None,"event_trigger_text":None,"model_score_metadata":None,"extraction_mode":"C"}]
