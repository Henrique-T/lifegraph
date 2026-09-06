from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.enums import CivilEventType, TemporalPrecision


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ExtractionRequest(StrictModel):
    text: str = Field(min_length=1, max_length=10_000)


class NormalizedTimeCandidate(StrictModel):
    start: datetime
    end: datetime
    temporal_precision: Literal["YEAR"]
    normalization_method: Literal["DETERMINISTIC_YEAR_PATTERN"]


class PipelineCandidate(StrictModel):
    event_type: CivilEventType
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


class PipelineExtractionResult(StrictModel):
    source_text: str
    model_id: str
    model_revision: str
    pipeline_id: Literal["LIFEGRAPH_PT_CIVIL_V1"]
    candidates: list[PipelineCandidate]
    warnings: list[str]
    latency_ms: float = Field(ge=0)


class ReviewStatus(StrEnum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"


class ReviewCandidate(PipelineCandidate):
    candidate_id: str
    review_status: ReviewStatus = ReviewStatus.PENDING


class ExtractionReview(StrictModel):
    extraction_id: str
    source_text: str
    model_id: str
    model_revision: str
    pipeline_id: Literal["LIFEGRAPH_PT_CIVIL_V1"]
    candidates: list[ReviewCandidate]
    warnings: list[str]
    latency_ms: float = Field(ge=0)
    expires_at: datetime


class CandidateCorrections(StrictModel):
    event_type: CivilEventType | None = None
    subject_text: str | None = Field(default=None, max_length=500)
    participant_texts: list[str] | None = None
    date_expression: str | None = Field(default=None, max_length=500)
    claimed_date_start: datetime | None = None
    claimed_date_end: datetime | None = None
    temporal_precision: TemporalPrecision | None = None
    temporal_uncertainty: bool | None = None

    @model_validator(mode="after")
    def validate_explicit_interval(self) -> "CandidateCorrections":
        interval_fields = {"claimed_date_start", "claimed_date_end", "temporal_precision"}
        supplied = interval_fields & self.model_fields_set
        if supplied and supplied != interval_fields:
            raise ValueError("Temporal correction requires start, end, and precision")
        return self


class CandidateAcceptanceRequest(StrictModel):
    person_id: str = Field(min_length=1)
    corrections: CandidateCorrections = Field(default_factory=CandidateCorrections)


class CandidateAcceptanceResult(StrictModel):
    extraction_id: str
    candidate_id: str
    person_id: str
    claim_event_id: str
    conversation_turn_id: str
    origin: Literal["CONVERSATION"]
    verification_status: Literal["DECLARED"]
    correction_applied: bool
    created: bool


class CandidateRejectionResult(StrictModel):
    extraction_id: str
    candidate_id: str
    review_status: Literal["REJECTED"]
    graph_delta_nodes: Literal[0] = 0
    graph_delta_edges: Literal[0] = 0
