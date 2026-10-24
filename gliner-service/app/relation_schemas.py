"""Internal schemas for development-only RelationCandidate extraction."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


RelationType = Literal[
    "FATHER_OF", "MOTHER_OF", "SON_OF", "DAUGHTER_OF",
    "BROTHER_OF", "SISTER_OF", "SPOUSE_OF",
]
EndpointSemanticTarget = Literal[
    "EXPLICIT_MENTION", "NARRATOR_ROLE", "UNRESOLVED_MENTION",
]


class StrictRelationModel(BaseModel):
    """Reject undeclared relation-extraction fields."""

    model_config = ConfigDict(extra="forbid")


class RelationDetection(StrictRelationModel):
    """Raw relation-expression evidence emitted by one detector."""

    text: str
    start: int = Field(ge=0)
    end: int = Field(gt=0)
    label: str
    confidence: float = Field(ge=0, le=1)


class RelationExtractRequest(StrictRelationModel):
    """Request for the frozen deterministic relation extractor."""

    text: str = Field(min_length=1, max_length=10_000)
    source_reference: str = Field(min_length=1, max_length=200)


class RelationCandidate(StrictRelationModel):
    """Temporary linguistic candidate; graph identities are intentionally absent."""

    candidate_id: str
    source_reference: str
    source_text: str
    relation_type: RelationType
    relation_surface_text: str
    relation_span_start: int = Field(ge=0)
    relation_span_end: int = Field(gt=0)
    endpoint_a_mention: str | None
    endpoint_a_span_start: int | None
    endpoint_a_span_end: int | None
    endpoint_a_resolution_state: Literal["RESOLVED_MENTION", "UNRESOLVED_MENTION"]
    endpoint_a_semantic_target: EndpointSemanticTarget = "EXPLICIT_MENTION"
    endpoint_b_mention: str | None
    endpoint_b_span_start: int | None
    endpoint_b_span_end: int | None
    endpoint_b_resolution_state: Literal["RESOLVED_MENTION", "UNRESOLVED_MENTION"]
    endpoint_b_semantic_target: EndpointSemanticTarget = "EXPLICIT_MENTION"
    polarity: Literal["POSITIVE", "NEGATED"]
    epistemic_status: Literal["ASSERTED", "UNCERTAIN", "HYPOTHETICAL"]
    reporting_mode: Literal["DIRECT", "REPORTED"]
    reporting_source_mention: str | None
    temporal_scope: Literal["CURRENT_OR_UNSPECIFIED", "PAST", "UNRESOLVED"]
    warnings: list[str]
    pipeline_id: Literal["LIFEGRAPH_PT_RELATION_V1_DEV", "LIFEGRAPH_PERSON_RELATION_V1"]
    model_id: str
    model_revision: str
    configuration_hash: str
    detector_strategy: Literal["A0", "B", "C", "D1"]
    detector_label: str
    detector_confidence: float = Field(ge=0, le=1)
    persistence_eligibility: str


class RelationExtractionResult(StrictRelationModel):
    """Detector evidence and downstream candidates for one narrative."""

    source_text: str
    strategy: Literal["A0", "B", "C", "D1"]
    threshold: float = Field(ge=0, le=1)
    detections: list[RelationDetection]
    candidates: list[RelationCandidate]
