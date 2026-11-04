"""Routes for deliberate deterministic reconciliation."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.reconciliation.engine import ReconciliationEngine
from app.reconciliation.schemas import ReconciliationResult

router = APIRouter()


def get_engine(request: Request) -> ReconciliationEngine:
    """Resolve the application-scoped reconciliation engine."""
    return request.app.state.reconciliation_engine


Engine = Annotated[ReconciliationEngine, Depends(get_engine)]


@router.post(
    "/claim-events/{claim_event_id}/reconcile",
    response_model=ReconciliationResult,
)
async def reconcile_claim(
    claim_event_id: str, engine: Engine
) -> ReconciliationResult:
    """Reconcile one claim through an explicit request."""
    return await engine.reconcile(claim_event_id)


@router.get(
    "/claim-events/{claim_event_id}/reconciliation",
    response_model=ReconciliationResult,
)
async def get_reconciliation(
    claim_event_id: str, engine: Engine
) -> ReconciliationResult:
    """Read the current reconciliation outcome for one claim."""
    return await engine.get_current(claim_event_id)
