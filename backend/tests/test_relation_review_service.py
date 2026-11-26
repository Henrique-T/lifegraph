"""Unit tests for temporary C1 person-relation review state."""

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
    RelationRejectionRequest,
    RelationReviewCorrections,
    RelationReviewStatus,
)
from app.relation_review.service import CONFIGURATION_HASH, RelationReviewService
from app.relations.enums import (
    EndpointMentionResolution,
    EndpointSemanticTarget,
    EpistemicStatus,
    PersistenceEligibility,
    RelationPolarity,
    RelationTemporalScope,
    RelationType,
    ReportingMode,
)
from app.relations.schemas import GroundedTextCorrection, RelationCandidate


SOURCE = "João é pai de Maria."


def candidate(**changes: object) -> RelationCandidate:
    values: dict[str, object] = {
        "candidate_id": "candidate-1",
        "source_reference": "review-upstream",
        "source_text": SOURCE,
        "relation_type": RelationType.FATHER_OF,
        "relation_surface_text": "pai de",
        "relation_span_start": 7,
        "relation_span_end": 13,
        "endpoint_a_mention": "João",
        "endpoint_a_span_start": 0,
        "endpoint_a_span_end": 4,
        "endpoint_a_resolution_state": EndpointMentionResolution.RESOLVED_MENTION,
        "endpoint_a_semantic_target": EndpointSemanticTarget.EXPLICIT_MENTION,
        "endpoint_b_mention": "Maria",
        "endpoint_b_span_start": 14,
        "endpoint_b_span_end": 19,
        "endpoint_b_resolution_state": EndpointMentionResolution.RESOLVED_MENTION,
        "endpoint_b_semantic_target": EndpointSemanticTarget.EXPLICIT_MENTION,
        "polarity": RelationPolarity.POSITIVE,
        "epistemic_status": EpistemicStatus.ASSERTED,
        "reporting_mode": ReportingMode.DIRECT,
        "temporal_scope": RelationTemporalScope.CURRENT_OR_UNSPECIFIED,
        "pipeline_id": "LIFEGRAPH_PERSON_RELATION_V1",
        "model_id": "deterministic-structural-baseline",
        "model_revision": "A0_B2+B3+B4+COMPOUND_NAMES",
        "configuration_hash": CONFIGURATION_HASH,
    }
    values.update(changes)
    return RelationCandidate.model_validate(values)


def person(person_id: str) -> PersonRead:
    return PersonRead(person_id=person_id, display_name=person_id, created_at=datetime(2026, 1, 1, tzinfo=UTC))


def service_with(*candidates: RelationCandidate, ttl: timedelta = timedelta(minutes=30)):
    client = AsyncMock()
    client.extract.return_value = list(candidates or (candidate(),))
    repository = AsyncMock()
    repository.ensure_relation_review_turn.return_value = ConversationTurnRead(
        conversation_turn_id="turn-1",
        text=SOURCE,
        speaker=Speaker.USER,
        review_extraction_id="review-upstream",
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )

    async def get_person(person_id: str):
        if person_id == "missing":
            raise DomainNotFoundError("Person not found")
        return person(person_id)

    repository.get_person.side_effect = get_person
    return RelationReviewService(client, repository, ttl=ttl), client, repository


async def make_review(service: RelationReviewService, text: str = SOURCE):
    return await service.extract(RelationExtractionRequest(text=text))


def accept_request(**changes: object) -> RelationAcceptanceRequest:
    values: dict[str, object] = {
        "endpoint_a_person_id": "person-a",
        "endpoint_b_person_id": "person-b",
        "reviewer_accepted": True,
    }
    values.update(changes)
    return RelationAcceptanceRequest.model_validate(values)


@pytest.mark.anyio
async def test_review_preserves_immutable_source_and_frozen_provenance() -> None:
    service, client, _ = service_with()
    review = await make_review(service)
    assert review.source_text == SOURCE
    assert review.conversation_turn_id == "turn-1"
    assert review.pipeline_id == "LIFEGRAPH_PERSON_RELATION_V1"
    assert review.model_revision == "A0_B2+B3+B4+COMPOUND_NAMES"
    assert review.configuration_hash == CONFIGURATION_HASH
    assert review.candidates[0].original_candidate.source_text == SOURCE
    assert review.candidates[0].review_status is RelationReviewStatus.PENDING
    client.extract.assert_awaited_once_with(SOURCE, review.review_id)


@pytest.mark.anyio
async def test_candidates_are_independent() -> None:
    second = candidate(candidate_id="candidate-2")
    service, _, _ = service_with(candidate(), second)
    review = await make_review(service)
    result = await service.reject(review.review_id, "candidate-1", RelationRejectionRequest(reason="wrong"))
    current = await service.get_review(review.review_id)
    assert result.review_status is RelationReviewStatus.REJECTED
    assert current.candidates[1].review_status is RelationReviewStatus.PENDING


@pytest.mark.anyio
async def test_valid_explicit_bindings_accept_without_graph_write() -> None:
    service, _, repository = service_with()
    review = await make_review(service)
    result = await service.accept(review.review_id, "candidate-1", accept_request())
    assert result.eligible is True
    assert result.review_status is RelationReviewStatus.ACCEPTED_FOR_PERSISTENCE
    assert result.primary_blocker is PersistenceEligibility.PERSISTIBLE
    assert result.graph_delta_nodes == result.graph_delta_edges == 0
    assert repository.get_person.await_count == 2
    assert all(call[0] in {"ensure_relation_review_turn", "get_person"} for call in repository.method_calls)


@pytest.mark.anyio
@pytest.mark.parametrize("side", ["endpoint_a_person_id", "endpoint_b_person_id"])
async def test_unknown_person_binding_is_rejected(side: str) -> None:
    service, _, _ = service_with()
    review = await make_review(service)
    with pytest.raises(DomainNotFoundError):
        await service.accept(review.review_id, "candidate-1", accept_request(**{side: "missing"}))


@pytest.mark.anyio
async def test_same_person_is_blocked_server_side() -> None:
    service, _, _ = service_with()
    review = await make_review(service)
    result = await service.accept(
        review.review_id, "candidate-1",
        accept_request(endpoint_a_person_id="same", endpoint_b_person_id="same"),
    )
    assert result.primary_blocker is PersistenceEligibility.NOT_PERSISTIBLE_SAME_PERSON_ENDPOINTS
    assert result.review_status is RelationReviewStatus.BLOCKED


@pytest.mark.anyio
async def test_missing_binding_is_blocked() -> None:
    service, _, _ = service_with()
    review = await make_review(service)
    result = await service.accept(
        review.review_id, "candidate-1", accept_request(endpoint_b_person_id=None)
    )
    assert result.primary_blocker is PersistenceEligibility.NOT_PERSISTIBLE_UNBOUND_ENDPOINT


@pytest.mark.anyio
async def test_narrator_role_requires_explicit_person_binding() -> None:
    text = "João é meu pai."
    narrator = candidate(
        source_text=text, relation_surface_text="pai", relation_span_start=11, relation_span_end=14,
        endpoint_b_mention="meu", endpoint_b_span_start=7, endpoint_b_span_end=10,
        endpoint_b_semantic_target=EndpointSemanticTarget.NARRATOR_ROLE,
    )
    service, _, repository = service_with(narrator)
    review = await make_review(service, text)
    blocked = await service.accept(review.review_id, "candidate-1", accept_request(endpoint_b_person_id=None))
    assert blocked.primary_blocker is PersistenceEligibility.NOT_PERSISTIBLE_UNBOUND_ENDPOINT
    assert repository.get_person.await_count == 1

    second = await make_review(service, text)
    accepted = await service.accept(second.review_id, "candidate-1", accept_request())
    assert accepted.eligible is True
    assert accepted.item.original_candidate.endpoint_b_semantic_target is EndpointSemanticTarget.NARRATOR_ROLE


@pytest.mark.anyio
async def test_unresolved_linguistic_endpoint_remains_blocked_even_when_bound() -> None:
    partial = candidate(
        endpoint_b_resolution_state=EndpointMentionResolution.UNRESOLVED_MENTION,
        endpoint_b_semantic_target=EndpointSemanticTarget.UNRESOLVED_MENTION,
    )
    service, _, _ = service_with(partial)
    review = await make_review(service)
    result = await service.accept(review.review_id, "candidate-1", accept_request())
    assert result.primary_blocker is PersistenceEligibility.NOT_PERSISTIBLE_PARTIAL_ENDPOINT


@pytest.mark.anyio
async def test_grounded_corrections_are_separate_from_original() -> None:
    service, _, _ = service_with()
    review = await make_review(service)
    corrections = RelationReviewCorrections(
        relation_surface=GroundedTextCorrection(text="pai de", start=7, end=13),
        endpoint_a=GroundedTextCorrection(text="João", start=0, end=4),
        endpoint_b=GroundedTextCorrection(text="Maria", start=14, end=19),
    )
    result = await service.accept(review.review_id, "candidate-1", accept_request(corrections=corrections))
    assert result.eligible is True
    assert result.item.original_candidate.endpoint_a_mention == "João"
    assert result.item.corrected_candidate is not None
    assert result.item.corrected_candidate is not result.item.original_candidate


@pytest.mark.anyio
@pytest.mark.parametrize(
    "correction",
    [
        GroundedTextCorrection(text="Pedro", start=0, end=5),
        GroundedTextCorrection(text="Maria", start=100, end=105),
    ],
)
async def test_ungrounded_endpoint_correction_is_blocked(correction: GroundedTextCorrection) -> None:
    service, _, _ = service_with()
    review = await make_review(service)
    result = await service.accept(
        review.review_id, "candidate-1",
        accept_request(corrections=RelationReviewCorrections(endpoint_a=correction)),
    )
    assert result.primary_blocker is PersistenceEligibility.NOT_PERSISTIBLE_UNGROUNDED_CORRECTION
    assert result.item.grounding_errors


@pytest.mark.anyio
async def test_ungrounded_relation_surface_correction_is_blocked() -> None:
    service, _, _ = service_with()
    review = await make_review(service)
    result = await service.accept(
        review.review_id, "candidate-1",
        accept_request(corrections=RelationReviewCorrections(
            relation_surface=GroundedTextCorrection(text="mãe de", start=7, end=13),
            relation_type=RelationType.MOTHER_OF,
        )),
    )
    assert result.primary_blocker is PersistenceEligibility.NOT_PERSISTIBLE_UNGROUNDED_CORRECTION


@pytest.mark.anyio
async def test_semantic_target_change_requires_grounded_support() -> None:
    service, _, _ = service_with()
    review = await make_review(service)
    with pytest.raises(DomainConflictError, match="SEMANTIC_TARGET_NOT_SUPPORTED"):
        await service.accept(
            review.review_id, "candidate-1",
            accept_request(corrections=RelationReviewCorrections(
                endpoint_a=GroundedTextCorrection(text="João", start=0, end=4),
                endpoint_a_semantic_target=EndpointSemanticTarget.NARRATOR_ROLE,
            )),
        )


@pytest.mark.anyio
async def test_relation_type_correction_must_normalize_from_grounded_surface() -> None:
    wrong = candidate(relation_type=RelationType.SON_OF)
    service, _, _ = service_with(wrong)
    review = await make_review(service)
    valid = await service.accept(
        review.review_id, "candidate-1",
        accept_request(corrections=RelationReviewCorrections(relation_type=RelationType.FATHER_OF)),
    )
    assert valid.eligible is True


@pytest.mark.anyio
async def test_unsupported_relation_type_correction_is_rejected() -> None:
    service, _, _ = service_with()
    review = await make_review(service)
    with pytest.raises(DomainConflictError, match="RELATION_TYPE_NOT_SUPPORTED"):
        await service.accept(
            review.review_id, "candidate-1",
            accept_request(corrections=RelationReviewCorrections(relation_type=RelationType.MOTHER_OF)),
        )


@pytest.mark.anyio
async def test_grounded_endpoint_swap_requires_opposite_original_spans() -> None:
    service, _, _ = service_with()
    review = await make_review(service)
    swap = RelationReviewCorrections(
        endpoint_a=GroundedTextCorrection(text="Maria", start=14, end=19),
        endpoint_b=GroundedTextCorrection(text="João", start=0, end=4),
        swap_endpoints=True,
    )
    result = await service.accept(review.review_id, "candidate-1", accept_request(corrections=swap))
    assert result.eligible is True
    assert result.item.corrected_candidate.endpoint_a_mention == "Maria"


@pytest.mark.anyio
async def test_ungrounded_endpoint_swap_is_rejected() -> None:
    service, _, _ = service_with()
    review = await make_review(service)
    with pytest.raises(DomainConflictError, match="ENDPOINT_SWAP"):
        await service.accept(
            review.review_id, "candidate-1",
            accept_request(corrections=RelationReviewCorrections(swap_endpoints=True)),
        )


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        ({"polarity": RelationPolarity.NEGATED}, PersistenceEligibility.NOT_PERSISTIBLE_NEGATED),
        ({"epistemic_status": EpistemicStatus.UNCERTAIN}, PersistenceEligibility.NOT_PERSISTIBLE_UNCERTAIN),
        ({"epistemic_status": EpistemicStatus.HYPOTHETICAL}, PersistenceEligibility.NOT_PERSISTIBLE_HYPOTHETICAL),
        ({"reporting_mode": ReportingMode.REPORTED}, PersistenceEligibility.NOT_PERSISTIBLE_REPORTED),
        ({"temporal_scope": RelationTemporalScope.PAST}, PersistenceEligibility.NOT_PERSISTIBLE_UNSUPPORTED_TEMPORAL_SCOPE),
        ({"temporal_scope": RelationTemporalScope.UNRESOLVED}, PersistenceEligibility.NOT_PERSISTIBLE_UNSUPPORTED_TEMPORAL_SCOPE),
    ],
)
async def test_frozen_semantic_blockers_cannot_be_overridden(changes, reason) -> None:
    service, _, _ = service_with(candidate(**changes))
    review = await make_review(service)
    result = await service.accept(review.review_id, "candidate-1", accept_request())
    assert result.primary_blocker is reason


@pytest.mark.anyio
async def test_question_candidate_is_reviewable_but_blocked() -> None:
    service, _, _ = service_with(candidate(epistemic_status=EpistemicStatus.UNCERTAIN))
    review = await make_review(service)
    result = await service.accept(review.review_id, "candidate-1", accept_request())
    assert result.primary_blocker is PersistenceEligibility.NOT_PERSISTIBLE_UNCERTAIN


@pytest.mark.anyio
async def test_accept_is_idempotent_only_for_identical_payload() -> None:
    service, _, _ = service_with()
    review = await make_review(service)
    request = accept_request()
    await service.accept(review.review_id, "candidate-1", request)
    replay = await service.accept(review.review_id, "candidate-1", request)
    assert replay.idempotent_replay is True
    with pytest.raises(DomainConflictError):
        await service.accept(
            review.review_id, "candidate-1", accept_request(endpoint_b_person_id="person-c")
        )


@pytest.mark.anyio
async def test_terminal_accept_reject_transitions() -> None:
    service, _, _ = service_with()
    accepted = await make_review(service)
    await service.accept(accepted.review_id, "candidate-1", accept_request())
    with pytest.raises(DomainConflictError):
        await service.reject(accepted.review_id, "candidate-1", RelationRejectionRequest())

    rejected = await make_review(service)
    first = await service.reject(rejected.review_id, "candidate-1", RelationRejectionRequest(reason="no"))
    replay = await service.reject(rejected.review_id, "candidate-1", RelationRejectionRequest(reason="changed"))
    assert first.idempotent_replay is False and replay.idempotent_replay is True
    with pytest.raises(DomainConflictError):
        await service.accept(rejected.review_id, "candidate-1", accept_request())


@pytest.mark.anyio
async def test_expired_unknown_review_and_candidate_are_rejected() -> None:
    service, _, _ = service_with(ttl=timedelta(seconds=-1))
    review = await make_review(service)
    with pytest.raises(DomainNotFoundError):
        await service.accept(review.review_id, "candidate-1", accept_request())
    with pytest.raises(DomainNotFoundError):
        await service.get_review("unknown")

    live, _, _ = service_with()
    current = await make_review(live)
    with pytest.raises(DomainNotFoundError):
        await live.accept(current.review_id, "unknown", accept_request())


@pytest.mark.parametrize(
    "extra",
    [
        {"origin": "CONVERSATION"},
        {"verification_status": "DECLARED"},
        {"pipeline_id": "attacker"},
        {"endpoint_a_person": {"display_name": "New person"}},
        {"evidence_text": "invented"},
        {"polarity": "POSITIVE"},
    ],
)
def test_acceptance_schema_rejects_security_sensitive_unknown_fields(extra) -> None:
    with pytest.raises(ValidationError):
        RelationAcceptanceRequest.model_validate({
            "endpoint_a_person_id": "a", "endpoint_b_person_id": "b",
            "reviewer_accepted": True, **extra,
        })


def test_corrections_schema_excludes_immutable_dimensions() -> None:
    for field in ("polarity", "epistemic_status", "reporting_mode", "temporal_scope"):
        with pytest.raises(ValidationError):
            RelationReviewCorrections.model_validate({field: "anything"})
