"""Strict runtime schemas for V1 conversational person relations."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.enums import Origin, VerificationStatus
from app.domain.schemas import ConversationTurnRead, PersonRead
from app.relations.canonical import canonical_pair_key, canonical_relation_family
from app.relations.enums import (
    CanonicalRelationFamily,
    EndpointMentionResolution,
    EndpointSemanticTarget,
    EpistemicStatus,
    PersistenceEligibility,
    RelationPolarity,
    RelationTemporalScope,
    RelationType,
    ReportingMode,
)


class RelationModel(BaseModel):
    """Base relation model that rejects undeclared fields."""

    model_config = ConfigDict(extra="forbid")


class GroundedTextCorrection(RelationModel):
    """Reviewer-selected text grounded by a half-open source span."""

    text: str = Field(min_length=1, max_length=10_000)
    start: int = Field(ge=0)
    end: int = Field(gt=0)

    @model_validator(mode="after")
    def validate_order(self) -> "GroundedTextCorrection":
        """Require a non-empty half-open interval."""

        if self.start >= self.end:
            raise ValueError("Correction start must be lower than end")
        return self

    def is_grounded_in(self, source_text: str) -> bool:
        """Check exact Python code-point offsets in an immutable source."""

        return self.end <= len(source_text) and source_text[self.start : self.end] == self.text


class RelationCandidateCorrections(RelationModel):
    """Optional corrected values kept separately from extracted provenance."""

    relation_type: RelationType | None = None
    relation_surface: GroundedTextCorrection | None = None
    endpoint_a: GroundedTextCorrection | None = None
    endpoint_b: GroundedTextCorrection | None = None


class RelationCandidate(RelationModel):
    """Temporary linguistic relation candidate with no graph identity binding."""

    candidate_id: str = Field(min_length=1, max_length=200)
    source_reference: str = Field(min_length=1, max_length=200)
    source_text: str = Field(min_length=1, max_length=10_000)
    relation_type: RelationType
    relation_surface_text: str = Field(min_length=1, max_length=500)
    relation_span_start: int = Field(ge=0)
    relation_span_end: int = Field(gt=0)
    endpoint_a_mention: str | None = Field(default=None, max_length=500)
    endpoint_a_span_start: int | None = Field(default=None, ge=0)
    endpoint_a_span_end: int | None = Field(default=None, gt=0)
    endpoint_a_resolution_state: EndpointMentionResolution
    endpoint_a_semantic_target: EndpointSemanticTarget = EndpointSemanticTarget.EXPLICIT_MENTION
    endpoint_b_mention: str | None = Field(default=None, max_length=500)
    endpoint_b_span_start: int | None = Field(default=None, ge=0)
    endpoint_b_span_end: int | None = Field(default=None, gt=0)
    endpoint_b_resolution_state: EndpointMentionResolution
    endpoint_b_semantic_target: EndpointSemanticTarget = EndpointSemanticTarget.EXPLICIT_MENTION
    polarity: RelationPolarity
    epistemic_status: EpistemicStatus
    reporting_mode: ReportingMode
    reporting_source_mention: str | None = Field(default=None, max_length=500)
    temporal_scope: RelationTemporalScope
    warnings: list[str] = Field(default_factory=list)
    pipeline_id: str = Field(min_length=1, max_length=200)
    model_id: str = Field(min_length=1, max_length=500)
    model_revision: str = Field(min_length=1, max_length=200)
    configuration_hash: str = Field(min_length=1, max_length=200)
    persistence_eligibility: PersistenceEligibility = (
        PersistenceEligibility.NOT_PERSISTIBLE_UNBOUND_ENDPOINT
    )

    @staticmethod
    def _validate_span(
        source_text: str,
        text: str,
        start: int,
        end: int,
        label: str,
    ) -> None:
        """Validate an exact half-open span against source text."""

        if not 0 <= start < end <= len(source_text):
            raise ValueError(f"{label} span is outside the source narrative")
        if source_text[start:end] != text:
            raise ValueError(f"{label} span does not match the source narrative")

    @classmethod
    def _validate_endpoint(
        cls,
        source_text: str,
        mention: str | None,
        start: int | None,
        end: int | None,
        resolution: EndpointMentionResolution,
        label: str,
    ) -> None:
        """Validate resolved and partial linguistic endpoint representations."""

        has_start = start is not None
        has_end = end is not None
        if has_start != has_end:
            raise ValueError(f"{label} span requires both start and end")
        if resolution is EndpointMentionResolution.RESOLVED_MENTION:
            if mention is None or start is None or end is None:
                raise ValueError(f"{label} resolved mention requires text and span")
        if start is not None and end is not None:
            if mention is None:
                raise ValueError(f"{label} span requires mention text")
            cls._validate_span(source_text, mention, start, end, label)

    @model_validator(mode="after")
    def validate_source_grounding(self) -> "RelationCandidate":
        """Ground all extracted linguistic evidence in the original narrative."""

        self._validate_span(
            self.source_text,
            self.relation_surface_text,
            self.relation_span_start,
            self.relation_span_end,
            "Relation",
        )
        self._validate_endpoint(
            self.source_text,
            self.endpoint_a_mention,
            self.endpoint_a_span_start,
            self.endpoint_a_span_end,
            self.endpoint_a_resolution_state,
            "Endpoint A",
        )
        self._validate_endpoint(
            self.source_text,
            self.endpoint_b_mention,
            self.endpoint_b_span_start,
            self.endpoint_b_span_end,
            self.endpoint_b_resolution_state,
            "Endpoint B",
        )
        return self


class RelationPersistenceProposal(RelationModel):
    """Pure eligibility input assembled after explicit reviewer choices."""

    candidate: RelationCandidate
    endpoint_a_person_id: str | None = Field(default=None, min_length=1, max_length=200)
    endpoint_b_person_id: str | None = Field(default=None, min_length=1, max_length=200)
    reviewer_accepted: bool = False
    corrections: RelationCandidateCorrections = Field(
        default_factory=RelationCandidateCorrections
    )


class RelationEligibilityDecision(RelationModel):
    """Deterministic persistence decision with one primary reason."""

    eligible: bool
    reason: PersistenceEligibility

    @model_validator(mode="after")
    def validate_consistency(self) -> "RelationEligibilityDecision":
        """Keep the eligibility flag consistent with its reason list."""

        if self.eligible != (self.reason is PersistenceEligibility.PERSISTIBLE):
            raise ValueError("Eligibility flag and reason are inconsistent")
        return self


class RelationClaim(RelationModel):
    """Future persisted conversational relation claim; no persistence is added here."""

    relation_claim_id: str = Field(min_length=1, max_length=200)
    relation_type: RelationType
    relation_surface_text: str = Field(min_length=1, max_length=500)
    source_text: str = Field(min_length=1, max_length=10_000)
    source_reference: str = Field(min_length=1, max_length=200)
    polarity: RelationPolarity
    epistemic_status: EpistemicStatus
    reporting_mode: ReportingMode
    temporal_scope: RelationTemporalScope
    origin: Origin = Origin.CONVERSATION
    verification_status: VerificationStatus = VerificationStatus.DECLARED
    endpoint_a_person_id: str = Field(min_length=1, max_length=200)
    endpoint_b_person_id: str = Field(min_length=1, max_length=200)
    conversation_turn_id: str = Field(min_length=1, max_length=200)
    original_relation_surface: str = Field(min_length=1, max_length=500)
    original_endpoint_a_mention: str | None = Field(default=None, max_length=500)
    original_endpoint_b_mention: str | None = Field(default=None, max_length=500)
    accepted_relation_surface: str = Field(min_length=1, max_length=500)
    accepted_endpoint_a_mention: str = Field(min_length=1, max_length=500)
    accepted_endpoint_b_mention: str = Field(min_length=1, max_length=500)
    accepted_relation_span_start: int = Field(ge=0)
    accepted_relation_span_end: int = Field(gt=0)
    accepted_endpoint_a_span_start: int = Field(ge=0)
    accepted_endpoint_a_span_end: int = Field(gt=0)
    accepted_endpoint_b_span_start: int = Field(ge=0)
    accepted_endpoint_b_span_end: int = Field(gt=0)
    endpoint_a_semantic_target: EndpointSemanticTarget
    endpoint_b_semantic_target: EndpointSemanticTarget
    reviewer_correction_applied: bool
    reviewer_corrections_json: str | None = None
    extraction_id: str = Field(min_length=1, max_length=200)
    candidate_id: str = Field(min_length=1, max_length=200)
    pipeline_id: str = Field(min_length=1, max_length=200)
    model_id: str = Field(min_length=1, max_length=500)
    model_revision: str = Field(min_length=1, max_length=200)
    configuration_hash: str = Field(min_length=1, max_length=200)
    acceptance_payload_hash: str = Field(min_length=1, max_length=200)
    persistence_operation_key: str = Field(min_length=1, max_length=200)
    review_id: str = Field(min_length=1, max_length=200)
    reviewed_at: datetime
    accepted_at: datetime
    canonical_relation_family: CanonicalRelationFamily
    canonical_pair_key: str = Field(min_length=1, max_length=700)
    created_at: datetime

    @model_validator(mode="after")
    def validate_v1_claim_invariants(self) -> "RelationClaim":
        """Enforce fixed conversational provenance and structural metadata."""

        if self.origin is not Origin.CONVERSATION:
            raise ValueError("RelationClaim origin must be CONVERSATION")
        if self.verification_status is not VerificationStatus.DECLARED:
            raise ValueError("RelationClaim verification status must be DECLARED")
        if self.endpoint_a_person_id == self.endpoint_b_person_id:
            raise ValueError("RelationClaim endpoints must reference different Persons")
        if self.polarity is not RelationPolarity.POSITIVE:
            raise ValueError("Persisted RelationClaim polarity must be POSITIVE")
        if self.epistemic_status is not EpistemicStatus.ASSERTED:
            raise ValueError("Persisted RelationClaim epistemic status must be ASSERTED")
        if self.reporting_mode is not ReportingMode.DIRECT:
            raise ValueError("Persisted RelationClaim reporting mode must be DIRECT")
        if self.temporal_scope is not RelationTemporalScope.CURRENT_OR_UNSPECIFIED:
            raise ValueError("Persisted RelationClaim temporal scope is unsupported")
        expected_family = canonical_relation_family(self.relation_type)
        if self.canonical_relation_family is not expected_family:
            raise ValueError("Canonical relation family does not match relation type")
        expected_key = canonical_pair_key(
            self.relation_type,
            self.endpoint_a_person_id,
            self.endpoint_b_person_id,
        )
        if self.canonical_pair_key != expected_key:
            raise ValueError("Canonical pair key does not match relation endpoints")
        for text, start, end, label in (
            (self.accepted_relation_surface, self.accepted_relation_span_start, self.accepted_relation_span_end, "Relation"),
            (self.accepted_endpoint_a_mention, self.accepted_endpoint_a_span_start, self.accepted_endpoint_a_span_end, "Endpoint A"),
            (self.accepted_endpoint_b_mention, self.accepted_endpoint_b_span_start, self.accepted_endpoint_b_span_end, "Endpoint B"),
        ):
            if not 0 <= start < end <= len(self.source_text):
                raise ValueError(f"{label} span is outside the source narrative")
            if self.source_text[start:end] != text:
                raise ValueError(f"{label} span does not match the source narrative")
        return self


class RelationClaimGraphRead(RelationModel):
    """One claim with its two role-specific endpoints and source turn."""

    claim: RelationClaim
    endpoint_a: PersonRead
    endpoint_b: PersonRead
    conversation_turn: ConversationTurnRead
