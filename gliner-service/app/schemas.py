from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ExtractRequest(StrictModel):
    text: str = Field(min_length=1, max_length=10_000)


class ModelSpan(StrictModel):
    label: str
    text: str
    start: int = Field(ge=0)
    end: int = Field(ge=0)
    score: float = Field(ge=0, le=1)


class NormalizedTimeCandidate(StrictModel):
    start: datetime
    end: datetime
    temporal_precision: Literal["YEAR"]
    normalization_method: str = "DETERMINISTIC_YEAR_PATTERN"


class ApprovedCandidate(StrictModel):
    event_type: Literal["nascimento", "casamento", "obito", "natimorto"]
    trigger_text: str
    trigger_start: int = Field(ge=0)
    trigger_end: int = Field(ge=0)
    subject_text: str | None
    subject_resolution: Literal["RESOLVED", "UNRESOLVED"]
    subject_reason: str
    participant_texts: list[str]
    date_expression: str | None
    normalized_time_candidate: NormalizedTimeCandidate | None
    model_score_metadata: float | None = None
    warnings: list[str]


class ApprovedExtractionResult(StrictModel):
    source_text: str
    model_id: str
    model_revision: str
    pipeline_id: Literal["LIFEGRAPH_PT_CIVIL_V1"]
    candidates: list[ApprovedCandidate]
    warnings: list[str]
    latency_ms: float = Field(ge=0)


class ExtractedEventCandidate(StrictModel):
    candidate_id: str
    event_type: Literal["nascimento", "casamento", "obito", "natimorto"]
    raw_event_text: str
    person_mentions: list[ModelSpan]
    temporal_expression: str | None
    normalized_time_candidate: NormalizedTimeCandidate | None
    uncertainty_detected: bool | None = None
    confidence: float
    raw_model_evidence: ModelSpan


class ExtractionResult(StrictModel):
    extraction_id: str
    source_text: str
    model_id: str
    model_revision: str
    extracted_events: list[ExtractedEventCandidate]
    raw_spans: list[ModelSpan]
    warnings: list[str]
    latency_ms: float


class CalibrationRequest(StrictModel):
    text: str = Field(min_length=1, max_length=10_000)
    configuration_id: Literal[
        "A_ENTITY_EVENT_BASELINE",
        "B_LINGUISTIC_EVENT_SPANS",
        "C_STRUCTURED_RECORDS",
        "D_CONSTRAINED_RECORDS",
        "E_RELATION_EXTRACTION",
    ]


class AssociationRequest(StrictModel):
    text: str = Field(min_length=1, max_length=10_000)
    strategy_id: Literal[
        "S1_DETERMINISTIC",
        "S1B_PORTUGUESE_CONTINUITY",
        "S1C_CONSERVATIVE_GUARDS",
        "S2_TRIGGER_RELATIONS",
        "S3_TRIGGER_RECORD",
        "S4_CONSERVATIVE_HYBRID",
    ]
