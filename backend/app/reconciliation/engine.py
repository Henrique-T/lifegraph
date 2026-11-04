"""Application service for explicit claim reconciliation."""

from app.graph.repository import GraphRepository
from app.reconciliation.rules import reconcile_candidates
from app.reconciliation.schemas import ReconciliationResult


class ReconciliationEngine:
    """Apply deterministic rules and persist their outcome."""

    def __init__(self, repository: GraphRepository) -> None:
        """Initialize the engine with its graph repository."""
        self._repository = repository

    async def reconcile(self, claim_event_id: str) -> ReconciliationResult:
        """Reconcile and persist one claim by identifier."""
        claim, candidates = await self._repository.get_reconciliation_context(
            claim_event_id
        )
        decision = reconcile_candidates(claim, candidates)
        return await self._repository.persist_reconciliation(
            claim_event_id, decision
        )

    async def get_current(self, claim_event_id: str) -> ReconciliationResult:
        """Read the currently persisted reconciliation result."""
        return await self._repository.get_reconciliation_result(claim_event_id)
