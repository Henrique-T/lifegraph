"""Schemas and reason codes for deterministic reconciliation."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import VerificationStatus


class ReasonCode(StrEnum):
    """Inspectable reasons emitted by reconciliation rules."""
    NO_MATCHING_REF_EVENT_TYPE = "NO_MATCHING_REF_EVENT_TYPE"
    EVENT_TYPE_MATCH = "EVENT_TYPE_MATCH"
    EVENT_DATE_WITHIN_CLAIM_INTERVAL = "EVENT_DATE_WITHIN_CLAIM_INTERVAL"
    EVENT_DATE_OUTSIDE_CLAIM_INTERVAL = "EVENT_DATE_OUTSIDE_CLAIM_INTERVAL"
    INSUFFICIENT_TEMPORAL_EVIDENCE = "INSUFFICIENT_TEMPORAL_EVIDENCE"
    UNIQUE_TEMPORALLY_COMPATIBLE_CANDIDATE = (
        "UNIQUE_TEMPORALLY_COMPATIBLE_CANDIDATE"
    )
    NO_TEMPORALLY_COMPATIBLE_REF_EVENT = "NO_TEMPORALLY_COMPATIBLE_REF_EVENT"
    AMBIGUOUS_MULTIPLE_REF_CANDIDATES = "AMBIGUOUS_MULTIPLE_REF_CANDIDATES"


class ReconciliationDecision(BaseModel):
    """Pure rule decision before graph persistence."""
    model_config = ConfigDict(extra="forbid")

    status: VerificationStatus
    matched_ref_event_id: str | None = None
    candidate_ref_event_ids: list[str]
    reason_codes: list[ReasonCode]
    contradictory_ref_event_ids: list[str] = Field(default_factory=list)


class ReconciliationResult(BaseModel):
    """Persisted reconciliation state returned to clients."""
    model_config = ConfigDict(extra="forbid")

    claim_event_id: str
    status: VerificationStatus
    matched_ref_event_id: str | None
    candidate_ref_event_ids: list[str]
    reason_codes: list[ReasonCode]
    reconciled_at: datetime
