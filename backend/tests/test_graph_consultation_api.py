"""Read-only API contract tests for independent graph consultation."""

from unittest.mock import AsyncMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes.domain import router
from app.domain.schemas import GraphRead


def test_graph_can_be_read_without_narrative_and_performs_only_read_operation() -> None:
    repository = AsyncMock()
    repository.get_graph.return_value = GraphRead(
        nodes=[
            {"id": "person-1", "type": "Person", "properties": {"display_name": "Ana"}},
            {"id": "claim-1", "type": "ClaimEvent", "properties": {"event_type": "nascimento"}},
        ],
        edges=[
            {"source": "person-1", "target": "claim-1", "type": "SUBJECT_OF", "properties": {}},
        ],
    )
    app = FastAPI()
    app.state.graph_repository = repository
    app.include_router(router)

    response = TestClient(app).get("/graph")

    assert response.status_code == 200
    assert response.json()["nodes"][0]["id"] == "person-1"
    assert response.json()["edges"][0]["type"] == "SUBJECT_OF"
    repository.get_graph.assert_awaited_once_with()
    for operation in (
        "create_person",
        "create_claim_event",
        "accept_extraction_candidate",
        "persist_reconciliation",
    ):
        getattr(repository, operation).assert_not_awaited()
