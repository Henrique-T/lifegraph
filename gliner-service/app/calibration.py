import asyncio
from dataclasses import dataclass
from time import perf_counter
from types import MappingProxyType
from typing import Literal

from app.model import ENTITY_LABELS, EVENT_LABEL_MAP, MODEL_ID, MODEL_REVISION

EVENT_TYPES = ("nascimento", "casamento", "obito", "natimorto")


@dataclass(frozen=True)
class CalibrationConfiguration:
    configuration_id: str
    mode: Literal["entities", "records", "relations"]
    definition: dict


_CONFIGURATIONS = {
    "A_ENTITY_EVENT_BASELINE": CalibrationConfiguration(
        "A_ENTITY_EVENT_BASELINE", "entities", dict(ENTITY_LABELS)
    ),
    "B_LINGUISTIC_EVENT_SPANS": CalibrationConfiguration(
        "B_LINGUISTIC_EVENT_SPANS",
        "entities",
        {
            "birth_expression": "Word or phrase explicitly expressing a human birth, such as nasceu or nasci",
            "marriage_expression": "Word or phrase explicitly expressing that a marriage occurred, such as casei, se casou, or casaram",
            "death_expression": "Word or phrase explicitly expressing a human death, such as morreu, faleceu, or óbito",
            "stillbirth_expression": "Word or phrase explicitly expressing a stillbirth or stillborn child",
            "person": "Named person or explicit human participant or subject mention, including kinship mentions",
            "date": "Explicit date, month, year, or temporal expression",
        },
    ),
    "C_STRUCTURED_RECORDS": CalibrationConfiguration(
        "C_STRUCTURED_RECORDS",
        "records",
        {"constrained": False},
    ),
    "D_CONSTRAINED_RECORDS": CalibrationConfiguration(
        "D_CONSTRAINED_RECORDS",
        "records",
        {"constrained": True},
    ),
    "E_RELATION_EXTRACTION": CalibrationConfiguration(
        "E_RELATION_EXTRACTION",
        "relations",
        {
            "birth_subject": "person or subject who was born",
            "marriage_subject": "person or subject who married",
            "death_subject": "person or subject who died",
            "stillbirth_subject": "stillborn child or subject of a stillbirth",
        },
    ),
}
CONFIGURATIONS = MappingProxyType(_CONFIGURATIONS)

B_EVENT_MAP = {
    "birth_expression": "nascimento",
    "marriage_expression": "casamento",
    "death_expression": "obito",
    "stillbirth_expression": "natimorto",
}
E_EVENT_MAP = {
    "birth_subject": "nascimento",
    "marriage_subject": "casamento",
    "death_subject": "obito",
    "stillbirth_subject": "natimorto",
}


def _entity_events(raw: dict, event_map: dict[str, str], mode: str) -> list[dict]:
    entities = raw.get("entities", {})
    people = entities.get("person", [])
    dates = entities.get("date", [])
    date = dates[0].get("text") if len(dates) == 1 else None
    events = []
    for label, event_type in event_map.items():
        for span in entities.get(label, []):
            events.append({
                "event_type": event_type,
                "subject_text": None,
                "participant_texts": [p.get("text") for p in people],
                "date_expression": date,
                "event_trigger_text": span.get("text"),
                "model_score_metadata": span.get("confidence"),
                "extraction_mode": mode,
            })
    return events


def _record_events(raw: dict, mode: str) -> list[dict]:
    records = raw.get("civil_event", [])
    if isinstance(records, dict):
        records = [records]
    events = []
    for record in records if isinstance(records, list) else []:
        def value(item):
            return item.get("text") if isinstance(item, dict) else item
        event_type = str(value(record.get("event_type", ""))).strip().casefold()
        if event_type not in EVENT_TYPES:
            continue
        participants = record.get("participant_texts") or []
        if isinstance(participants, str):
            participants = [participants]
        participants = [value(item) for item in participants if value(item)]
        events.append({
            "event_type": event_type,
            "subject_text": value(record.get("subject_text")) or None,
            "participant_texts": participants,
            "date_expression": value(record.get("date_expression")) or None,
            "event_trigger_text": value(record.get("trigger_text")) or None,
            "model_score_metadata": None,
            "extraction_mode": mode,
        })
    return events


def _relation_events(raw: dict, mode: str) -> list[dict]:
    rels = raw.get("relation_extraction", {})
    events = []
    for label, event_type in E_EVENT_MAP.items():
        for relation in rels.get(label, []):
            head = relation.get("head", {})
            tail = relation.get("tail", {})
            events.append({
                "event_type": event_type,
                "subject_text": head.get("text") or None,
                "participant_texts": [tail.get("text")] if tail.get("text") else [],
                "date_expression": None,
                "event_trigger_text": None,
                "model_score_metadata": relation.get("confidence") or head.get("confidence"),
                "extraction_mode": mode,
            })
    return events


def build_record_schema(model, constrained: bool):
    schema = model.create_schema()
    record = schema.structure("civil_event", mode="natural", anchor="event_type")
    choices = list(EVENT_TYPES) if constrained else None
    record.field("event_type", dtype="str", choices=choices, description="Civil event type: nascimento, casamento, obito, or natimorto", cardinality="required_one")
    record.field("subject_text", dtype="str", description="Exact text naming the person or subject to whom the event happened", cardinality="optional_one")
    record.field("participant_texts", dtype="list", description="Other people explicitly participating in the event", cardinality="zero_or_more")
    record.field("date_expression", dtype="str", description="Date or temporal expression exactly as written", cardinality="optional_one")
    record.field("trigger_text", dtype="str", description="Words explicitly expressing that the event occurred", cardinality="optional_one")
    return schema


async def extract_configuration(service, config: CalibrationConfiguration, text: str) -> dict:
    started = perf_counter()
    async with service._lock:
        if config.mode == "entities":
            raw = await asyncio.to_thread(service._model.extract_entities, text, config.definition, include_confidence=True, include_spans=True)
            mapping = EVENT_LABEL_MAP if config.configuration_id.startswith("A_") else B_EVENT_MAP
            events = _entity_events(raw, mapping, config.configuration_id)
        elif config.mode == "records":
            schema = build_record_schema(service._model, config.definition["constrained"])
            raw = await asyncio.to_thread(service._model.extract, text, schema, include_confidence=True, include_spans=True)
            events = _record_events(raw, config.configuration_id)
        else:
            raw = await asyncio.to_thread(service._model.extract_relations, text, config.definition, include_confidence=True, include_spans=True)
            events = _relation_events(raw, config.configuration_id)
    return {
        "configuration_id": config.configuration_id,
        "model_id": MODEL_ID,
        "model_revision": MODEL_REVISION,
        "detected_events": events,
        "raw_output": raw,
        "latency_ms": (perf_counter() - started) * 1000,
    }
