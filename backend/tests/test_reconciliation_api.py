"""HTTP contract tests for explicit ClaimEvent reconciliation."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from app.api.routes.reconciliation import router
from app.graph.repository import DomainNotFoundError
from app.reconciliation.schemas import ReconciliationResult


def _result() -> ReconciliationResult:
    return ReconciliationResult(
        claim_event_id="claim-1",
        status="CONFIRMED",
        matched_ref_event_id="ref-1",
        candidate_ref_event_ids=["ref-1"],
        reason_codes=["EVENT_TYPE_MATCH", "EVENT_DATE_WITHIN_CLAIM_INTERVAL"],
        reconciled_at=datetime(2026, 11, 3, 12, 0, tzinfo=timezone.utc),
    )


def _client() -> tuple[TestClient, AsyncMock]:
    engine = AsyncMock()
    engine.reconcile.return_value = _result()
    engine.get_current.return_value = _result()
    app = FastAPI()
    app.state.reconciliation_engine = engine

    @app.exception_handler(DomainNotFoundError)
    async def missing(_request: Request, exception: DomainNotFoundError) -> JSONResponse:
        return JSONResponse({"detail": str(exception)}, status_code=status.HTTP_404_NOT_FOUND)

    app.include_router(router)
    return TestClient(app), engine


def test_post_explicitly_reconciles_and_returns_server_authoritative_result() -> None:
    client, engine = _client()
    response = client.post(
        "/claim-events/claim-1/reconcile",
        json={"status": "DIVERGENT", "reason_codes": ["client-controlled"]},
    )

    assert response.status_code == 200
    assert response.json() == {
        "claim_event_id": "claim-1",
        "status": "CONFIRMED",
        "matched_ref_event_id": "ref-1",
        "candidate_ref_event_ids": ["ref-1"],
        "reason_codes": ["EVENT_TYPE_MATCH", "EVENT_DATE_WITHIN_CLAIM_INTERVAL"],
        "reconciled_at": "2026-11-03T12:00:00Z",
    }
    engine.reconcile.assert_awaited_once_with("claim-1")
    engine.get_current.assert_not_awaited()


def test_post_unknown_claim_event_returns_not_found() -> None:
    client, engine = _client()
    engine.reconcile.side_effect = DomainNotFoundError("ClaimEvent not found")
    response = client.post("/claim-events/missing/reconcile")
    assert response.status_code == 404
    assert response.json() == {"detail": "ClaimEvent not found"}


def test_get_returns_latest_persisted_reconciliation_contract() -> None:
    client, engine = _client()
    response = client.get("/claim-events/claim-1/reconciliation")
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {
        "claim_event_id",
        "status",
        "matched_ref_event_id",
        "candidate_ref_event_ids",
        "reason_codes",
        "reconciled_at",
    }
    assert body["claim_event_id"] == "claim-1"
    assert body["matched_ref_event_id"] == "ref-1"
    engine.get_current.assert_awaited_once_with("claim-1")
    engine.reconcile.assert_not_awaited()


def test_get_unknown_or_unreconciled_claim_event_returns_not_found() -> None:
    client, engine = _client()
    engine.get_current.side_effect = DomainNotFoundError("ClaimEvent has not been reconciled")
    response = client.get("/claim-events/unreconciled/reconciliation")
    assert response.status_code == 404
    assert response.json() == {"detail": "ClaimEvent has not been reconciled"}
