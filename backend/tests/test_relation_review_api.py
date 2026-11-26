"""HTTP contract tests for C1 relation review."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from app.api.routes.relation_review import router
from app.domain.enums import Speaker
from app.domain.schemas import ConversationTurnRead, PersonRead
from app.graph.repository import DomainConflictError, DomainNotFoundError
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


def candidate() -> RelationCandidate:
    return RelationCandidate(
        candidate_id="candidate-1", source_reference="upstream", source_text=TEXT,
        relation_type=RelationType.FATHER_OF, relation_surface_text="pai de",
        relation_span_start=7, relation_span_end=13,
        endpoint_a_mention="João", endpoint_a_span_start=0, endpoint_a_span_end=4,
        endpoint_a_resolution_state=EndpointMentionResolution.RESOLVED_MENTION,
        endpoint_a_semantic_target=EndpointSemanticTarget.EXPLICIT_MENTION,
        endpoint_b_mention="Maria", endpoint_b_span_start=14, endpoint_b_span_end=19,
        endpoint_b_resolution_state=EndpointMentionResolution.RESOLVED_MENTION,
        endpoint_b_semantic_target=EndpointSemanticTarget.EXPLICIT_MENTION,
        polarity=RelationPolarity.POSITIVE, epistemic_status=EpistemicStatus.ASSERTED,
        reporting_mode=ReportingMode.DIRECT,
        temporal_scope=RelationTemporalScope.CURRENT_OR_UNSPECIFIED,
        pipeline_id="LIFEGRAPH_PERSON_RELATION_V1",
        model_id="deterministic-structural-baseline", model_revision="A0_B2+B3+B4+COMPOUND_NAMES",
        configuration_hash=CONFIGURATION_HASH,
    )


def build_client() -> tuple[TestClient, AsyncMock]:
    extractor = AsyncMock()
    extractor.extract.return_value = [candidate()]
    repository = AsyncMock()
    repository.ensure_relation_review_turn.return_value = ConversationTurnRead(
        conversation_turn_id="turn-1", text=TEXT, speaker=Speaker.USER,
        review_extraction_id="upstream", created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )

    async def get_person(person_id: str):
        if person_id == "missing":
            raise DomainNotFoundError("Person not found")
        return PersonRead(
            person_id=person_id, display_name=person_id,
            created_at=datetime(2026, 1, 1, tzinfo=UTC),
        )

    repository.get_person.side_effect = get_person

    async def persist_relation_claim(claim):
        return RelationClaimGraphRead(
            claim=claim,
            endpoint_a=await get_person(claim.endpoint_a_person_id),
            endpoint_b=await get_person(claim.endpoint_b_person_id),
            conversation_turn=ConversationTurnRead(
                conversation_turn_id=claim.conversation_turn_id, text=claim.source_text,
                speaker=Speaker.USER, review_extraction_id=claim.review_id,
                created_at=claim.created_at,
            ),
        ), True

    repository.persist_relation_claim.side_effect = persist_relation_claim
    service = RelationReviewService(extractor, repository)
    app = FastAPI()
    app.state.relation_review_service = service

    @app.exception_handler(DomainNotFoundError)
    async def missing(_request: Request, exc: DomainNotFoundError):
        return JSONResponse({"detail": str(exc)}, status_code=status.HTTP_404_NOT_FOUND)

    @app.exception_handler(DomainConflictError)
    async def conflict(_request: Request, exc: DomainConflictError):
        return JSONResponse({"detail": str(exc)}, status_code=status.HTTP_409_CONFLICT)

    app.include_router(router)
    return TestClient(app), repository


def create_review(client: TestClient) -> tuple[str, str]:
    response = client.post("/relation-extractions", json={"text": TEXT})
    assert response.status_code == 201
    payload = response.json()
    return payload["review_id"], payload["candidates"][0]["candidate_id"]


def test_relation_extraction_and_get_contract() -> None:
    client, _ = build_client()
    review_id, candidate_id = create_review(client)
    payload = client.get(f"/relation-reviews/{review_id}").json()
    assert payload["source_text"] == TEXT
    assert payload["configuration_hash"] == CONFIGURATION_HASH
    assert payload["candidates"][0]["candidate_id"] == candidate_id
    assert payload["candidates"][0]["review_status"] == "PENDING"


def test_accept_contract_is_review_only_and_graph_delta_zero() -> None:
    client, repository = build_client()
    review_id, candidate_id = create_review(client)
    response = client.post(
        f"/relation-reviews/{review_id}/candidates/{candidate_id}/accept",
        json={
            "endpoint_a_person_id": "person-a", "endpoint_b_person_id": "person-b",
            "reviewer_accepted": True,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["review_status"] == "ACCEPTED_FOR_PERSISTENCE"
    assert payload["eligible"] is True
    assert payload["graph_delta_nodes"] == payload["graph_delta_edges"] == 0
    assert all(call[0] in {"ensure_relation_review_turn", "get_person"} for call in repository.method_calls)


def test_reject_contract_is_terminal_temporary_state() -> None:
    client, _ = build_client()
    review_id, candidate_id = create_review(client)
    response = client.post(
        f"/relation-reviews/{review_id}/candidates/{candidate_id}/reject",
        json={"reason": "not a declaration"},
    )
    assert response.status_code == 200
    assert response.json()["review_status"] == "REJECTED"
    assert response.json()["graph_delta_nodes"] == 0


def test_unknown_person_and_same_person_are_server_validated() -> None:
    client, _ = build_client()
    review_id, candidate_id = create_review(client)
    missing = client.post(
        f"/relation-reviews/{review_id}/candidates/{candidate_id}/accept",
        json={"endpoint_a_person_id": "missing", "endpoint_b_person_id": "b", "reviewer_accepted": True},
    )
    assert missing.status_code == 404

    same = client.post(
        f"/relation-reviews/{review_id}/candidates/{candidate_id}/accept",
        json={"endpoint_a_person_id": "same", "endpoint_b_person_id": "same", "reviewer_accepted": True},
    )
    assert same.status_code == 200
    assert same.json()["primary_blocker"] == "NOT_PERSISTIBLE_SAME_PERSON_ENDPOINTS"


def test_unknown_review_and_candidate_return_404() -> None:
    client, _ = build_client()
    assert client.get("/relation-reviews/unknown").status_code == 404
    review_id, _ = create_review(client)
    response = client.post(
        f"/relation-reviews/{review_id}/candidates/unknown/accept",
        json={"endpoint_a_person_id": "a", "endpoint_b_person_id": "b", "reviewer_accepted": True},
    )
    assert response.status_code == 404


def test_api_rejects_overrides_and_unexpected_fields() -> None:
    client, _ = build_client()
    review_id, candidate_id = create_review(client)
    for field in ("origin", "verification_status", "pipeline_id", "polarity", "new_person"):
        response = client.post(
            f"/relation-reviews/{review_id}/candidates/{candidate_id}/accept",
            json={
                "endpoint_a_person_id": "a", "endpoint_b_person_id": "b",
                "reviewer_accepted": True, field: "forbidden",
            },
        )
        assert response.status_code == 422


def test_api_rejects_invalid_correction_spans_without_crashing() -> None:
    client, _ = build_client()
    review_id, candidate_id = create_review(client)
    response = client.post(
        f"/relation-reviews/{review_id}/candidates/{candidate_id}/accept",
        json={
            "endpoint_a_person_id": "a", "endpoint_b_person_id": "b", "reviewer_accepted": True,
            "corrections": {"endpoint_a": {"text": "invented", "start": 0, "end": 8}},
        },
    )
    assert response.status_code == 200
    assert response.json()["primary_blocker"] == "NOT_PERSISTIBLE_UNGROUNDED_CORRECTION"


def test_persist_endpoint_consumes_server_state_with_empty_body() -> None:
    client, _ = build_client()
    review_id, candidate_id = create_review(client)
    accepted = client.post(
        f"/relation-reviews/{review_id}/candidates/{candidate_id}/accept",
        json={"endpoint_a_person_id": "a", "endpoint_b_person_id": "b", "reviewer_accepted": True},
    )
    assert accepted.status_code == 200
    response = client.post(
        f"/relation-reviews/{review_id}/candidates/{candidate_id}/persist", json={}
    )
    assert response.status_code == 200
    assert response.json()["persistence_status"] == "PERSISTED"
    assert response.json()["origin"] == "CONVERSATION"
    assert response.json()["verification_status"] == "DECLARED"


def test_persist_endpoint_rejects_semantic_override_payload() -> None:
    client, _ = build_client()
    review_id, candidate_id = create_review(client)
    response = client.post(
        f"/relation-reviews/{review_id}/candidates/{candidate_id}/persist",
        json={"relation_type": "FATHER_OF"},
    )
    assert response.status_code == 422
