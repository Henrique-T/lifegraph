from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.enums import (
    CivilEventType,
    Origin,
    Speaker,
    TemporalPrecision,
    VerificationStatus,
)


def _is_aware(value: datetime) -> bool:
    return value.tzinfo is not None and value.utcoffset() is not None


class DomainModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PersonCreate(DomainModel):
    display_name: str = Field(min_length=1, max_length=200)


class PersonRead(PersonCreate):
    person_id: str
    created_at: datetime
    external_ref_person_id: str | None = None


class ConversationTurnCreate(DomainModel):
    text: str = Field(min_length=1, max_length=10_000)
    speaker: Speaker


class ConversationTurnRead(ConversationTurnCreate):
    conversation_turn_id: str
    created_at: datetime
    review_extraction_id: str | None = None


class ClaimEventCreate(DomainModel):
    event_type: CivilEventType
    origin: Origin = Origin.CONVERSATION
    verification_status: VerificationStatus = VerificationStatus.DECLARED
    claimed_date_start: datetime | None = None
    claimed_date_end: datetime | None = None
    temporal_precision: TemporalPrecision = TemporalPrecision.UNKNOWN
    temporal_uncertainty: bool = False

    @model_validator(mode="after")
    def validate_temporal_interval(self) -> "ClaimEventCreate":
        has_start = self.claimed_date_start is not None
        has_end = self.claimed_date_end is not None
        if self.temporal_precision is TemporalPrecision.UNKNOWN:
            if has_start or has_end:
                raise ValueError("UNKNOWN temporal precision cannot have an interval")
            return self
        if not has_start or not has_end:
            raise ValueError("Known temporal precision requires start and end")
        assert self.claimed_date_start is not None
        assert self.claimed_date_end is not None
        if not _is_aware(self.claimed_date_start) or not _is_aware(self.claimed_date_end):
            raise ValueError("Claim temporal values must be timezone-aware")
        if self.claimed_date_start > self.claimed_date_end:
            raise ValueError("Claim temporal interval start must not exceed end")
        return self


class ClaimEventRead(ClaimEventCreate):
    claim_event_id: str
    created_at: datetime
    reconciled_at: datetime | None = None
    matched_ref_event_id: str | None = None
    reconciliation_candidate_ref_event_ids: list[str] | None = None
    reconciliation_reason_codes: list[str] | None = None
    accepted_extraction_candidate_key: str | None = None
    extraction_id: str | None = None
    candidate_id: str | None = None
    pipeline_id: str | None = None
    model_id: str | None = None
    model_revision: str | None = None
    original_event_type: CivilEventType | None = None
    original_trigger_text: str | None = None
    original_subject_text: str | None = None
    original_subject_resolution: str | None = None
    original_subject_reason: str | None = None
    original_participant_texts: list[str] | None = None
    original_date_expression: str | None = None
    original_model_score_metadata: float | None = None
    reviewer_correction_applied: bool | None = None
    reviewer_corrections_json: str | None = None
    acceptance_payload_hash: str | None = None


class RefEventCreate(DomainModel):
    external_ref_id: str = Field(min_length=1, max_length=200)
    event_type: CivilEventType
    origin: Origin = Origin.REF
    event_date: datetime | None = None
    registration_date: datetime

    @model_validator(mode="after")
    def require_ref_origin(self) -> "RefEventCreate":
        if self.origin is not Origin.REF:
            raise ValueError("RefEvent origin must be REF")
        if self.event_date is not None and not _is_aware(self.event_date):
            raise ValueError("RefEvent event_date must be timezone-aware")
        if not _is_aware(self.registration_date):
            raise ValueError("RefEvent registration_date must be timezone-aware")
        return self


class RefEventRead(RefEventCreate):
    ref_event_id: str
    created_at: datetime


class EvidenceCreate(DomainModel):
    evidence_type: str = Field(min_length=1, max_length=100)
    description: str = Field(min_length=1, max_length=1_000)
    source: str | None = Field(default=None, min_length=1, max_length=100)
    evidence_key: str | None = Field(default=None, min_length=1, max_length=500)


class EvidenceRead(EvidenceCreate):
    evidence_id: str
    created_at: datetime


class ParticipationCreate(DomainModel):
    role: str = Field(min_length=1, max_length=100)


class RelationshipRead(DomainModel):
    source: str
    relationship: str
    target: str
    properties: dict[str, Any] = Field(default_factory=dict)


class GraphNode(DomainModel):
    id: str
    type: str
    properties: dict[str, Any]


class GraphEdge(DomainModel):
    source: str
    target: str
    type: str
    properties: dict[str, Any]


class GraphRead(DomainModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]
