"""In-memory relation review, explicit binding, and eligibility orchestration."""

from __future__ import annotations

import asyncio
import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.graph.repository import DomainConflictError, DomainNotFoundError, GraphRepository
from app.relation_review.client import RelationExtractionClient
from app.relation_review.schemas import (
    RelationAcceptanceRequest,
    RelationExtractionRequest,
    RelationRejectionRequest,
    RelationReviewActionResult,
    RelationReviewCorrections,
    RelationReviewItem,
    RelationReviewSession,
    RelationReviewStatus,
    RelationPersistenceResult,
    RelationPersistenceStatus,
)
from app.domain.enums import Origin, VerificationStatus
from app.relations.canonical import canonical_pair_key, canonical_relation_family
from app.relations.eligibility import evaluate_relation_persistence
from app.relations.enums import (
    EndpointMentionResolution,
    EndpointSemanticTarget,
    PersistenceEligibility,
    RelationType,
)
from app.relations.schemas import (
    GroundedTextCorrection,
    RelationCandidate,
    RelationCandidateCorrections,
    RelationPersistenceProposal,
    RelationClaim,
)

REVIEW_TTL = timedelta(minutes=30)
PIPELINE_ID = "LIFEGRAPH_PERSON_RELATION_V1"
MODEL_REVISION = "A0_B2+B3+B4+COMPOUND_NAMES"
CONFIGURATION_HASH = "95E09B3C9AC2AB853432045A96B1F9D4C2F995AA6BDC6CDF9CE33BDE6820B728"

_SURFACE_TYPES = {
    "pai": RelationType.FATHER_OF,
    "mãe": RelationType.MOTHER_OF,
    "filho": RelationType.SON_OF,
    "filha": RelationType.DAUGHTER_OF,
    "irmão": RelationType.BROTHER_OF,
    "irmã": RelationType.SISTER_OF,
    "marido": RelationType.SPOUSE_OF,
    "esposa": RelationType.SPOUSE_OF,
    "cônjuge": RelationType.SPOUSE_OF,
}
_UNRESOLVED_SURFACE = re.compile(r"^(?:ele|ela|dele|dela|quem|alguém|uma\s+pessoa)\b", re.I)
_NARRATOR_SURFACE = re.compile(r"^(?:meu|minha)$", re.I)


def _surface_relation_type(text: str) -> RelationType | None:
    """Normalize one grounded relation phrase for correction validation only."""

    found = {kind for token, kind in _SURFACE_TYPES.items() if re.search(rf"\b{token}\b", text, re.I)}
    return next(iter(found)) if len(found) == 1 else None


def _semantic_target_for(text: str) -> EndpointSemanticTarget:
    """Classify corrected evidence without resolving any graph identity."""

    if _NARRATOR_SURFACE.fullmatch(text.strip()):
        return EndpointSemanticTarget.NARRATOR_ROLE
    if _UNRESOLVED_SURFACE.match(text.strip()):
        return EndpointSemanticTarget.UNRESOLVED_MENTION
    return EndpointSemanticTarget.EXPLICIT_MENTION


def _grounding_errors(source: str, corrections: RelationReviewCorrections) -> list[str]:
    """Return every corrected span that is not an exact source substring."""

    errors = []
    for name, correction in (
        ("relation_surface", corrections.relation_surface),
        ("endpoint_a", corrections.endpoint_a),
        ("endpoint_b", corrections.endpoint_b),
    ):
        if correction is not None and not correction.is_grounded_in(source):
            errors.append(f"{name} is not grounded in the immutable source narrative")
    return errors


class RelationReviewService:
    """Own temporary reviews without ever writing RelationClaim graph data."""

    def __init__(
        self,
        client: RelationExtractionClient,
        repository: GraphRepository,
        *,
        ttl: timedelta = REVIEW_TTL,
    ) -> None:
        self._client = client
        self._repository = repository
        self._ttl = ttl
        self._reviews: dict[str, RelationReviewSession] = {}
        self._lock = asyncio.Lock()

    async def extract(self, request: RelationExtractionRequest) -> RelationReviewSession:
        """Run the frozen extractor and create independent temporary review items."""

        review_id = str(uuid4())
        candidates = await self._client.extract(request.text, review_id)
        source_turn = await self._repository.ensure_relation_review_turn(
            review_id=review_id,
            source_text=request.text,
        )
        now = datetime.now(timezone.utc)
        expires = now + self._ttl
        review = RelationReviewSession(
            review_id=review_id,
            source_text=request.text,
            conversation_turn_id=source_turn.conversation_turn_id,
            pipeline_id=PIPELINE_ID,
            model_id="deterministic-structural-baseline",
            model_revision=MODEL_REVISION,
            configuration_hash=CONFIGURATION_HASH,
            candidates=[
                RelationReviewItem(
                    review_id=review_id,
                    candidate_id=candidate.candidate_id,
                    source_text=request.text,
                    original_candidate=candidate,
                    created_at=now,
                    expires_at=expires,
                )
                for candidate in candidates
            ],
            created_at=now,
            expires_at=expires,
        )
        async with self._lock:
            self._reviews[review_id] = review
        return review.model_copy(deep=True)

    async def get_review(self, review_id: str) -> RelationReviewSession:
        """Return a review copy or reject missing and expired sessions."""

        async with self._lock:
            review = self._reviews.get(review_id)
            if review is None or review.expires_at <= datetime.now(timezone.utc):
                self._reviews.pop(review_id, None)
                raise DomainNotFoundError("Relation review not found or expired")
            return review.model_copy(deep=True)

    @staticmethod
    def _candidate(review: RelationReviewSession, candidate_id: str) -> RelationReviewItem:
        item = next((candidate for candidate in review.candidates if candidate.candidate_id == candidate_id), None)
        if item is None:
            raise DomainNotFoundError("Relation review candidate not found")
        return item

    @staticmethod
    def _validate_semantic_target(
        correction: GroundedTextCorrection | None,
        requested: EndpointSemanticTarget | None,
    ) -> None:
        if requested is None:
            return
        if correction is None:
            raise DomainConflictError("SEMANTIC_TARGET_CORRECTION_REQUIRES_GROUNDED_ENDPOINT")
        if _semantic_target_for(correction.text) is not requested:
            raise DomainConflictError("SEMANTIC_TARGET_NOT_SUPPORTED_BY_GROUNDED_TEXT")

    @staticmethod
    def _validate_swap(candidate: RelationCandidate, corrections: RelationReviewCorrections) -> None:
        if not corrections.swap_endpoints:
            return
        if corrections.endpoint_a is None or corrections.endpoint_b is None:
            raise DomainConflictError("ENDPOINT_SWAP_REQUIRES_BOTH_GROUNDED_SPANS")
        original_a = (
            candidate.endpoint_a_mention,
            candidate.endpoint_a_span_start,
            candidate.endpoint_a_span_end,
        )
        original_b = (
            candidate.endpoint_b_mention,
            candidate.endpoint_b_span_start,
            candidate.endpoint_b_span_end,
        )
        corrected_a = (corrections.endpoint_a.text, corrections.endpoint_a.start, corrections.endpoint_a.end)
        corrected_b = (corrections.endpoint_b.text, corrections.endpoint_b.start, corrections.endpoint_b.end)
        if corrected_a != original_b or corrected_b != original_a:
            raise DomainConflictError("ENDPOINT_SWAP_NOT_SUPPORTED_BY_ORIGINAL_GROUNDED_SPANS")

    @classmethod
    def _effective_candidate(
        cls,
        candidate: RelationCandidate,
        corrections: RelationReviewCorrections,
    ) -> RelationCandidate:
        """Build a corrected copy while preserving immutable semantic dimensions."""

        cls._validate_semantic_target(corrections.endpoint_a, corrections.endpoint_a_semantic_target)
        cls._validate_semantic_target(corrections.endpoint_b, corrections.endpoint_b_semantic_target)
        cls._validate_swap(candidate, corrections)
        surface = corrections.relation_surface.text if corrections.relation_surface else candidate.relation_surface_text
        relation_type = corrections.relation_type or candidate.relation_type
        if corrections.relation_surface is not None or corrections.relation_type is not None:
            if _surface_relation_type(surface) is not relation_type:
                raise DomainConflictError("RELATION_TYPE_NOT_SUPPORTED_BY_GROUNDED_SURFACE")

        values = candidate.model_dump()
        values.update({"relation_type": relation_type, "relation_surface_text": surface})
        if corrections.relation_surface:
            values.update({"relation_span_start": corrections.relation_surface.start,
                           "relation_span_end": corrections.relation_surface.end})
        for side in ("a", "b"):
            correction = getattr(corrections, f"endpoint_{side}")
            requested_target = getattr(corrections, f"endpoint_{side}_semantic_target")
            if correction:
                target = requested_target or _semantic_target_for(correction.text)
                values.update({
                    f"endpoint_{side}_mention": correction.text,
                    f"endpoint_{side}_span_start": correction.start,
                    f"endpoint_{side}_span_end": correction.end,
                    f"endpoint_{side}_semantic_target": target,
                    f"endpoint_{side}_resolution_state": (
                        EndpointMentionResolution.UNRESOLVED_MENTION
                        if target is EndpointSemanticTarget.UNRESOLVED_MENTION
                        else EndpointMentionResolution.RESOLVED_MENTION
                    ),
                })
        return RelationCandidate.model_validate(values)

    @staticmethod
    def _payload_hash(request: RelationAcceptanceRequest) -> str:
        return hashlib.sha256(
            json.dumps(request.model_dump(mode="json"), sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()

    async def accept(
        self,
        review_id: str,
        candidate_id: str,
        request: RelationAcceptanceRequest,
    ) -> RelationReviewActionResult:
        """Evaluate one explicit review decision without graph persistence."""

        review = await self.get_review(review_id)
        item = self._candidate(review, candidate_id)
        payload_hash = self._payload_hash(request)
        if item.review_status is RelationReviewStatus.REJECTED:
            raise DomainConflictError("REJECTED_RELATION_CANDIDATE_CONFLICT")
        if item.review_status is RelationReviewStatus.ACCEPTED_FOR_PERSISTENCE:
            if item.accepted_payload_hash != payload_hash:
                raise DomainConflictError("ACCEPTED_RELATION_CANDIDATE_CONFLICT")
            return RelationReviewActionResult(
                review_id=review_id, candidate_id=candidate_id,
                review_status=item.review_status, eligible=True,
                primary_blocker=PersistenceEligibility.PERSISTIBLE,
                item=item, idempotent_replay=True,
            )

        person_a = await self._repository.get_person(request.endpoint_a_person_id) if request.endpoint_a_person_id else None
        person_b = await self._repository.get_person(request.endpoint_b_person_id) if request.endpoint_b_person_id else None
        errors = _grounding_errors(review.source_text, request.corrections)
        corrected = None
        if not errors:
            corrected = self._effective_candidate(item.original_candidate, request.corrections)
        eligibility_corrections = RelationCandidateCorrections(
            relation_type=request.corrections.relation_type,
            relation_surface=request.corrections.relation_surface,
            endpoint_a=request.corrections.endpoint_a,
            endpoint_b=request.corrections.endpoint_b,
        )
        proposal = RelationPersistenceProposal(
            candidate=corrected or item.original_candidate,
            endpoint_a_person_id=request.endpoint_a_person_id,
            endpoint_b_person_id=request.endpoint_b_person_id,
            reviewer_accepted=request.reviewer_accepted,
            corrections=eligibility_corrections,
        )
        decision = evaluate_relation_persistence(proposal)
        status = (
            RelationReviewStatus.ACCEPTED_FOR_PERSISTENCE
            if decision.eligible else RelationReviewStatus.BLOCKED
        )
        async with self._lock:
            stored = self._candidate(self._reviews[review_id], candidate_id)
            stored.corrected_candidate = corrected
            stored.corrections = request.corrections
            stored.endpoint_a_person = person_a
            stored.endpoint_b_person = person_b
            stored.review_status = status
            stored.eligible = decision.eligible
            stored.primary_blocker = decision.reason
            stored.grounding_errors = errors
            if decision.eligible:
                stored.accepted_payload_hash = payload_hash
                stored.accepted_at = datetime.now(timezone.utc)
            response_item = stored.model_copy(deep=True)
        return RelationReviewActionResult(
            review_id=review_id, candidate_id=candidate_id,
            review_status=status, eligible=decision.eligible,
            primary_blocker=decision.reason, item=response_item,
        )

    async def reject(
        self,
        review_id: str,
        candidate_id: str,
        request: RelationRejectionRequest,
    ) -> RelationReviewActionResult:
        """Terminally reject one candidate without graph mutation."""

        await self.get_review(review_id)
        async with self._lock:
            item = self._candidate(self._reviews[review_id], candidate_id)
            if item.review_status is RelationReviewStatus.ACCEPTED_FOR_PERSISTENCE:
                raise DomainConflictError("ACCEPTED_RELATION_CANDIDATE_CONFLICT")
            replay = item.review_status is RelationReviewStatus.REJECTED
            if not replay:
                item.review_status = RelationReviewStatus.REJECTED
                item.rejection_reason = request.reason
                item.eligible = False
                item.primary_blocker = PersistenceEligibility.NOT_PERSISTIBLE_NOT_ACCEPTED
            response_item = item.model_copy(deep=True)
        return RelationReviewActionResult(
            review_id=review_id, candidate_id=candidate_id,
            review_status=RelationReviewStatus.REJECTED, eligible=False,
            primary_blocker=PersistenceEligibility.NOT_PERSISTIBLE_NOT_ACCEPTED,
            item=response_item, idempotent_replay=replay,
        )

    @staticmethod
    def _persistence_operation_key(
        review: RelationReviewSession,
        item: RelationReviewItem,
        candidate: RelationCandidate,
    ) -> str:
        """Hash the accepted operation, not its semantic canonical pair."""

        assert item.endpoint_a_person is not None
        assert item.endpoint_b_person is not None
        material = {
            "review_id": review.review_id,
            "candidate_id": item.candidate_id,
            "conversation_turn_id": review.conversation_turn_id,
            "accepted_payload_hash": item.accepted_payload_hash,
            "candidate": candidate.model_dump(mode="json"),
            "endpoint_a_person_id": item.endpoint_a_person.person_id,
            "endpoint_b_person_id": item.endpoint_b_person.person_id,
            "pipeline_id": review.pipeline_id,
            "model_revision": review.model_revision,
            "configuration_hash": review.configuration_hash,
        }
        return hashlib.sha256(
            json.dumps(material, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()

    async def persist(
        self,
        review_id: str,
        candidate_id: str,
    ) -> RelationPersistenceResult:
        """Persist one accepted review as a declared claim, never as a fact edge."""

        review = await self.get_review(review_id)
        item = self._candidate(review, candidate_id)
        if item.review_status is not RelationReviewStatus.ACCEPTED_FOR_PERSISTENCE:
            raise DomainConflictError("RELATION_CANDIDATE_NOT_ACCEPTED_FOR_PERSISTENCE")
        if not item.eligible or item.accepted_payload_hash is None or item.accepted_at is None:
            raise DomainConflictError("RELATION_CANDIDATE_NOT_ELIGIBLE_FOR_PERSISTENCE")
        if item.endpoint_a_person is None or item.endpoint_b_person is None:
            raise DomainConflictError("RELATION_CANDIDATE_BINDINGS_UNAVAILABLE")
        candidate = item.corrected_candidate or item.original_candidate
        assert candidate.endpoint_a_mention is not None
        assert candidate.endpoint_b_mention is not None
        assert candidate.endpoint_a_span_start is not None
        assert candidate.endpoint_a_span_end is not None
        assert candidate.endpoint_b_span_start is not None
        assert candidate.endpoint_b_span_end is not None
        operation_key = self._persistence_operation_key(review, item, candidate)
        now = datetime.now(timezone.utc)
        relation_claim_id = item.relation_claim_id or str(uuid4())
        claim = RelationClaim(
            relation_claim_id=relation_claim_id,
            relation_type=candidate.relation_type,
            relation_surface_text=candidate.relation_surface_text,
            source_text=review.source_text,
            source_reference=candidate.source_reference,
            polarity=candidate.polarity,
            epistemic_status=candidate.epistemic_status,
            reporting_mode=candidate.reporting_mode,
            temporal_scope=candidate.temporal_scope,
            origin=Origin.CONVERSATION,
            verification_status=VerificationStatus.DECLARED,
            endpoint_a_person_id=item.endpoint_a_person.person_id,
            endpoint_b_person_id=item.endpoint_b_person.person_id,
            conversation_turn_id=review.conversation_turn_id,
            original_relation_surface=item.original_candidate.relation_surface_text,
            original_endpoint_a_mention=item.original_candidate.endpoint_a_mention,
            original_endpoint_b_mention=item.original_candidate.endpoint_b_mention,
            accepted_relation_surface=candidate.relation_surface_text,
            accepted_endpoint_a_mention=candidate.endpoint_a_mention,
            accepted_endpoint_b_mention=candidate.endpoint_b_mention,
            accepted_relation_span_start=candidate.relation_span_start,
            accepted_relation_span_end=candidate.relation_span_end,
            accepted_endpoint_a_span_start=candidate.endpoint_a_span_start,
            accepted_endpoint_a_span_end=candidate.endpoint_a_span_end,
            accepted_endpoint_b_span_start=candidate.endpoint_b_span_start,
            accepted_endpoint_b_span_end=candidate.endpoint_b_span_end,
            endpoint_a_semantic_target=candidate.endpoint_a_semantic_target,
            endpoint_b_semantic_target=candidate.endpoint_b_semantic_target,
            reviewer_correction_applied=request_corrections_applied(item.corrections),
            reviewer_corrections_json=json.dumps(
                item.corrections.model_dump(mode="json"), sort_keys=True
            ),
            extraction_id=review.review_id,
            candidate_id=item.candidate_id,
            pipeline_id=review.pipeline_id,
            model_id=review.model_id,
            model_revision=review.model_revision,
            configuration_hash=review.configuration_hash,
            acceptance_payload_hash=item.accepted_payload_hash,
            persistence_operation_key=operation_key,
            review_id=review.review_id,
            reviewed_at=item.accepted_at,
            accepted_at=item.accepted_at,
            canonical_relation_family=canonical_relation_family(candidate.relation_type),
            canonical_pair_key=canonical_pair_key(
                candidate.relation_type,
                item.endpoint_a_person.person_id,
                item.endpoint_b_person.person_id,
            ),
            created_at=now,
        )
        graph, created = await self._repository.persist_relation_claim(claim)
        async with self._lock:
            stored = self._candidate(self._reviews[review_id], candidate_id)
            stored.persistence_status = RelationPersistenceStatus.PERSISTED
            stored.relation_claim_id = graph.claim.relation_claim_id
            stored.persisted_at = graph.claim.created_at
        return RelationPersistenceResult(
            review_id=review_id,
            candidate_id=candidate_id,
            relation_claim_id=graph.claim.relation_claim_id,
            conversation_turn_id=graph.conversation_turn.conversation_turn_id,
            review_status=RelationReviewStatus.ACCEPTED_FOR_PERSISTENCE,
            persistence_status=RelationPersistenceStatus.PERSISTED,
            relation_type=graph.claim.relation_type,
            endpoint_a_person_id=graph.endpoint_a.person_id,
            endpoint_b_person_id=graph.endpoint_b.person_id,
            canonical_pair_key=graph.claim.canonical_pair_key,
            origin=graph.claim.origin.value,
            verification_status=graph.claim.verification_status.value,
            pipeline_id=graph.claim.pipeline_id,
            model_revision=graph.claim.model_revision,
            configuration_hash=graph.claim.configuration_hash,
            persisted_at=graph.claim.created_at,
            idempotent_replay=not created,
            graph_delta_nodes=1 if created else 0,
            graph_delta_edges=3 if created else 0,
        )


def request_corrections_applied(corrections: RelationReviewCorrections) -> bool:
    """Return whether a reviewer supplied any correction field."""

    return any(value not in (None, False) for value in corrections.model_dump().values())
