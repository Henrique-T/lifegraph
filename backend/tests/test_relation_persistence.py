"""C2 service tests for persistent, declared RelationClaim nodes."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError

from app.domain.enums import Speaker
from app.domain.schemas import ConversationTurnRead, PersonRead
from app.graph.repository import DomainConflictError, DomainNotFoundError
from app.relation_review.schemas import (
    RelationAcceptanceRequest,
    RelationExtractionRequest,
    RelationPersistenceRequest,
    RelationPersistenceStatus,
    RelationRejectionRequest,
)
from app.relation_review.service import CONFIGURATION_HASH, RelationReviewService
from app.relations.enums import (
    EndpointMentionResolution,
    EndpointSemanticTarget,
    EpistemicStatus,
    RelationPolarity,
    RelationTemporalScope,
    RelationType,
    ReportingMode,
)
from app.relations.schemas import RelationCandidate, RelationClaimGraphRead


TEXT = "João é pai de Maria."
NOW = datetime(2026, 1, 1, tzinfo=UTC)


def candidate(**changes: object) -> RelationCandidate:
    values: dict[str, object] = {
        "candidate_id": "candidate-1", "source_reference": "source-1", "source_text": TEXT,
        "relation_type": RelationType.FATHER_OF, "relation_surface_text": "pai de",
        "relation_span_start": 7, "relation_span_end": 13,
        "endpoint_a_mention": "João", "endpoint_a_span_start": 0, "endpoint_a_span_end": 4,
        "endpoint_a_resolution_state": EndpointMentionResolution.RESOLVED_MENTION,
        "endpoint_a_semantic_target": EndpointSemanticTarget.EXPLICIT_MENTION,
        "endpoint_b_mention": "Maria", "endpoint_b_span_start": 14, "endpoint_b_span_end": 19,
        "endpoint_b_resolution_state": EndpointMentionResolution.RESOLVED_MENTION,
        "endpoint_b_semantic_target": EndpointSemanticTarget.EXPLICIT_MENTION,
        "polarity": RelationPolarity.POSITIVE, "epistemic_status": EpistemicStatus.ASSERTED,
        "reporting_mode": ReportingMode.DIRECT,
        "temporal_scope": RelationTemporalScope.CURRENT_OR_UNSPECIFIED,
        "pipeline_id": "LIFEGRAPH_PERSON_RELATION_V1", "model_id": "deterministic-structural-baseline",
        "model_revision": "A0_B2+B3+B4+COMPOUND_NAMES", "configuration_hash": CONFIGURATION_HASH,
    }
    values.update(changes)
    return RelationCandidate.model_validate(values)


def person(person_id: str) -> PersonRead:
    return PersonRead(person_id=person_id, display_name=person_id, created_at=NOW)


def build_service(*candidates: RelationCandidate, ttl: timedelta = timedelta(minutes=30)):
    extractor = AsyncMock()
    extractor.extract.return_value = list(candidates or (candidate(),))
    repository = AsyncMock()
    turn_counter = 0

    async def ensure_turn(*, review_id: str, source_text: str):
        nonlocal turn_counter
        turn_counter += 1
        return ConversationTurnRead(
            conversation_turn_id=f"turn-{turn_counter}", text=source_text,
            speaker=Speaker.USER, review_extraction_id=review_id, created_at=NOW,
        )

    async def get_person(person_id: str):
        if person_id.startswith("missing"):
            raise DomainNotFoundError("Person not found")
        return person(person_id)

    persisted: dict[str, RelationClaimGraphRead] = {}

    async def persist_relation_claim(claim):
        if claim.endpoint_a_person_id.startswith("deleted") or claim.endpoint_b_person_id.startswith("deleted"):
            raise DomainNotFoundError("RelationClaim endpoint Person or source ConversationTurn not found")
        existing = persisted.get(claim.persistence_operation_key)
        if existing:
            return existing, False
        graph = RelationClaimGraphRead(
            claim=claim,
            endpoint_a=person(claim.endpoint_a_person_id),
            endpoint_b=person(claim.endpoint_b_person_id),
            conversation_turn=ConversationTurnRead(
                conversation_turn_id=claim.conversation_turn_id,
                text=claim.source_text,
                speaker=Speaker.USER,
                review_extraction_id=claim.review_id,
                created_at=NOW,
            ),
        )
        persisted[claim.persistence_operation_key] = graph
        return graph, True

    repository.ensure_relation_review_turn.side_effect = ensure_turn
    repository.get_person.side_effect = get_person
    repository.persist_relation_claim.side_effect = persist_relation_claim
    return RelationReviewService(extractor, repository, ttl=ttl), repository, persisted


async def accept(service: RelationReviewService, *, a: str = "person-a", b: str = "person-b"):
    review = await service.extract(RelationExtractionRequest(text=TEXT))
    await service.accept(
        review.review_id, review.candidates[0].candidate_id,
        RelationAcceptanceRequest(endpoint_a_person_id=a, endpoint_b_person_id=b, reviewer_accepted=True),
    )
    return review


@pytest.mark.anyio
async def test_accepted_claim_persists_as_declared_conversational_node() -> None:
    service, repository, _ = build_service()
    review = await accept(service)
    result = await service.persist(review.review_id, "candidate-1")
    claim = repository.persist_relation_claim.await_args.args[0]
    assert result.persistence_status is RelationPersistenceStatus.PERSISTED
    assert result.origin == "CONVERSATION" and result.verification_status == "DECLARED"
    assert claim.origin.value == "CONVERSATION" and claim.verification_status.value == "DECLARED"
    assert claim.endpoint_a_person_id == "person-a" and claim.endpoint_b_person_id == "person-b"
    assert claim.conversation_turn_id == review.conversation_turn_id
    assert claim.canonical_relation_family.value == "PARENT_CHILD"
    assert claim.endpoint_a_semantic_target is EndpointSemanticTarget.EXPLICIT_MENTION
    assert result.graph_delta_nodes == 1 and result.graph_delta_edges == 3


@pytest.mark.anyio
async def test_same_operation_replay_returns_same_claim_without_duplicate_delta() -> None:
    service, _, persisted = build_service()
    review = await accept(service)
    first = await service.persist(review.review_id, "candidate-1")
    second = await service.persist(review.review_id, "candidate-1")
    assert second.relation_claim_id == first.relation_claim_id
    assert first.idempotent_replay is False and second.idempotent_replay is True
    assert second.graph_delta_nodes == second.graph_delta_edges == 0
    assert len(persisted) == 1


@pytest.mark.anyio
async def test_independent_declarations_keep_distinct_claims_and_provenance() -> None:
    service, _, persisted = build_service()
    first_review = await accept(service)
    second_review = await accept(service)
    first = await service.persist(first_review.review_id, "candidate-1")
    second = await service.persist(second_review.review_id, "candidate-1")
    assert first.relation_claim_id != second.relation_claim_id
    assert first.conversation_turn_id != second.conversation_turn_id
    assert first.canonical_pair_key == second.canonical_pair_key
    assert len(persisted) == 2


@pytest.mark.anyio
@pytest.mark.parametrize("state", ["pending", "blocked", "rejected"])
async def test_nonaccepted_review_states_cannot_persist(state: str) -> None:
    relation = candidate(epistemic_status=EpistemicStatus.UNCERTAIN) if state == "blocked" else candidate()
    service, repository, _ = build_service(relation)
    review = await service.extract(RelationExtractionRequest(text=TEXT))
    if state == "blocked":
        await service.accept(
            review.review_id, "candidate-1",
            RelationAcceptanceRequest(endpoint_a_person_id="a", endpoint_b_person_id="b", reviewer_accepted=True),
        )
    elif state == "rejected":
        await service.reject(review.review_id, "candidate-1", RelationRejectionRequest(reason="no"))
    with pytest.raises(DomainConflictError, match="NOT_ACCEPTED"):
        await service.persist(review.review_id, "candidate-1")
    repository.persist_relation_claim.assert_not_awaited()


@pytest.mark.anyio
async def test_expired_lost_unknown_review_and_candidate_cannot_persist() -> None:
    service, repository, _ = build_service(ttl=timedelta(seconds=-1))
    review = await service.extract(RelationExtractionRequest(text=TEXT))
    with pytest.raises(DomainNotFoundError):
        await service.persist(review.review_id, "candidate-1")
    with pytest.raises(DomainNotFoundError):
        await service.persist("lost-after-restart", "candidate-1")
    repository.persist_relation_claim.assert_not_awaited()

    live, _, _ = build_service()
    accepted = await accept(live)
    with pytest.raises(DomainNotFoundError):
        await live.persist(accepted.review_id, "unknown")


@pytest.mark.anyio
@pytest.mark.parametrize("deleted", [("deleted-a", "b"), ("a", "deleted-b")])
async def test_endpoint_person_is_revalidated_inside_persistence(deleted) -> None:
    service, _, persisted = build_service()
    review = await accept(service, a=deleted[0], b=deleted[1])
    with pytest.raises(DomainNotFoundError):
        await service.persist(review.review_id, "candidate-1")
    assert persisted == {}


@pytest.mark.anyio
async def test_narrator_semantic_target_is_preserved_without_autobinding() -> None:
    text = "João é meu pai."
    narrator = candidate(
        source_text=text, relation_surface_text="pai", relation_span_start=11, relation_span_end=14,
        endpoint_b_mention="meu", endpoint_b_span_start=7, endpoint_b_span_end=10,
        endpoint_b_semantic_target=EndpointSemanticTarget.NARRATOR_ROLE,
    )
    service, repository, _ = build_service(narrator)
    review = await service.extract(RelationExtractionRequest(text=text))
    await service.accept(
        review.review_id, "candidate-1",
        RelationAcceptanceRequest(
            endpoint_a_person_id="joao-explicit", endpoint_b_person_id="narrator-explicit",
            reviewer_accepted=True,
        ),
    )
    await service.persist(review.review_id, "candidate-1")
    claim = repository.persist_relation_claim.await_args.args[0]
    assert claim.endpoint_b_semantic_target is EndpointSemanticTarget.NARRATOR_ROLE
    assert claim.endpoint_b_person_id == "narrator-explicit"


@pytest.mark.anyio
async def test_question_cannot_bypass_review_eligibility() -> None:
    service, repository, _ = build_service(candidate(epistemic_status=EpistemicStatus.UNCERTAIN))
    review = await service.extract(RelationExtractionRequest(text=TEXT))
    await service.accept(
        review.review_id, "candidate-1",
        RelationAcceptanceRequest(endpoint_a_person_id="a", endpoint_b_person_id="b", reviewer_accepted=True),
    )
    with pytest.raises(DomainConflictError):
        await service.persist(review.review_id, "candidate-1")
    repository.persist_relation_claim.assert_not_awaited()


@pytest.mark.parametrize(
    "payload",
    [
        {"origin": "CONVERSATION"}, {"verification_status": "DECLARED"},
        {"relation_type": "FATHER_OF"}, {"endpoint_a_person_id": "override"},
        {"pipeline_id": "override"}, {"graph_id": "override"},
    ],
)
def test_empty_persistence_command_rejects_all_overrides(payload) -> None:
    with pytest.raises(ValidationError):
        RelationPersistenceRequest.model_validate(payload)


def test_empty_persistence_command_accepts_only_empty_object() -> None:
    assert RelationPersistenceRequest.model_validate({}).model_dump() == {}
