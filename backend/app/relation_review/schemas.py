"""Strict API and temporary-state schemas for relation review."""

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.domain.schemas import PersonRead
from app.relations.enums import EndpointSemanticTarget, PersistenceEligibility, RelationType
from app.relations.schemas import GroundedTextCorrection, RelationCandidate


class StrictReviewModel(BaseModel):
    """Reject fields outside the explicit relation-review contract."""

    model_config = ConfigDict(extra="forbid")


class RelationExtractionRequest(StrictReviewModel):
    """Immutable narrative submitted to the frozen relation extractor."""

    text: str = Field(min_length=1, max_length=10_000)


class RelationReviewStatus(StrEnum):
    """Finite state for one independently reviewed relation candidate."""

    PENDING = "PENDING"
    BLOCKED = "BLOCKED"
    ACCEPTED_FOR_PERSISTENCE = "ACCEPTED_FOR_PERSISTENCE"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class RelationPersistenceStatus(StrEnum):
    """Orthogonal graph-persistence state for an accepted review item."""

    NOT_PERSISTED = "NOT_PERSISTED"
    PERSISTED = "PERSISTED"


class RelationReviewCorrections(StrictReviewModel):
    """C1-correctable values; epistemic and provenance fields are absent."""

    relation_type: RelationType | None = None
    relation_surface: GroundedTextCorrection | None = None
    endpoint_a: GroundedTextCorrection | None = None
    endpoint_b: GroundedTextCorrection | None = None
    endpoint_a_semantic_target: EndpointSemanticTarget | None = None
    endpoint_b_semantic_target: EndpointSemanticTarget | None = None
    swap_endpoints: bool = False


class RelationAcceptanceRequest(StrictReviewModel):
    """Two explicit existing-Person bindings plus optional grounded corrections."""

    endpoint_a_person_id: str | None = Field(default=None, min_length=1, max_length=200)
    endpoint_b_person_id: str | None = Field(default=None, min_length=1, max_length=200)
    reviewer_accepted: Literal[True]
    corrections: RelationReviewCorrections = Field(default_factory=RelationReviewCorrections)


class RelationRejectionRequest(StrictReviewModel):
    """Optional human-readable rejection reason."""

    reason: str | None = Field(default=None, min_length=1, max_length=500)


class RelationReviewItem(StrictReviewModel):
    """One temporary candidate with separate review decisions and provenance."""

    review_id: str
    candidate_id: str
    source_text: str
    original_candidate: RelationCandidate
    corrected_candidate: RelationCandidate | None = None
    corrections: RelationReviewCorrections = Field(default_factory=RelationReviewCorrections)
    endpoint_a_person: PersonRead | None = None
    endpoint_b_person: PersonRead | None = None
    review_status: RelationReviewStatus = RelationReviewStatus.PENDING
    eligible: bool = False
    primary_blocker: PersistenceEligibility = PersistenceEligibility.NOT_PERSISTIBLE_NOT_ACCEPTED
    grounding_errors: list[str] = Field(default_factory=list)
    rejection_reason: str | None = None
    created_at: datetime
    expires_at: datetime
    accepted_payload_hash: str | None = None
    accepted_at: datetime | None = None
    persistence_status: RelationPersistenceStatus = RelationPersistenceStatus.NOT_PERSISTED
    relation_claim_id: str | None = None
    persisted_at: datetime | None = None
    graph_delta_nodes: Literal[0] = 0
    graph_delta_edges: Literal[0] = 0


class RelationReviewSession(StrictReviewModel):
    """Expiring in-memory review session containing independent candidates."""

    review_id: str
    source_text: str
    conversation_turn_id: str
    pipeline_id: Literal["LIFEGRAPH_PERSON_RELATION_V1"]
    model_id: str
    model_revision: Literal["A0_B2+B3+B4"]
    configuration_hash: Literal["32040A53D33F30A4DDDBA0E423180AB9DC08AF17B583BB6B3A9A82BEA091FC7D"]
    candidates: list[RelationReviewItem]
    created_at: datetime
    expires_at: datetime


class RelationReviewActionResult(StrictReviewModel):
    """Outcome of a temporary accept/reject action; never a graph write result."""

    review_id: str
    candidate_id: str
    review_status: RelationReviewStatus
    eligible: bool
    primary_blocker: PersistenceEligibility
    item: RelationReviewItem
    idempotent_replay: bool = False
    graph_delta_nodes: Literal[0] = 0
    graph_delta_edges: Literal[0] = 0


class RelationPersistenceRequest(StrictReviewModel):
    """Empty persistence command; accepted semantics cannot be resubmitted."""


class RelationPersistenceResult(StrictReviewModel):
    """Readback of an idempotent RelationClaim persistence operation."""

    review_id: str
    candidate_id: str
    relation_claim_id: str
    conversation_turn_id: str
    review_status: Literal[RelationReviewStatus.ACCEPTED_FOR_PERSISTENCE]
    persistence_status: Literal[RelationPersistenceStatus.PERSISTED]
    relation_type: RelationType
    endpoint_a_person_id: str
    endpoint_b_person_id: str
    canonical_pair_key: str
    origin: Literal["CONVERSATION"]
    verification_status: Literal["DECLARED"]
    pipeline_id: Literal["LIFEGRAPH_PERSON_RELATION_V1"]
    model_revision: Literal["A0_B2+B3+B4"]
    configuration_hash: Literal["32040A53D33F30A4DDDBA0E423180AB9DC08AF17B583BB6B3A9A82BEA091FC7D"]
    persisted_at: datetime
    idempotent_replay: bool
    graph_delta_nodes: Literal[0, 1]
    graph_delta_edges: Literal[0, 3]
