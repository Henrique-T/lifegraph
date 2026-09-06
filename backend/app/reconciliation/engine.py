from app.graph.repository import GraphRepository
from app.reconciliation.rules import reconcile_candidates
from app.reconciliation.schemas import ReconciliationResult


class ReconciliationEngine:
    def __init__(self, repository: GraphRepository) -> None:
        self._repository = repository

    async def reconcile(self, claim_event_id: str) -> ReconciliationResult:
        claim, candidates = await self._repository.get_reconciliation_context(
            claim_event_id
        )
        decision = reconcile_candidates(claim, candidates)
        return await self._repository.persist_reconciliation(
            claim_event_id, decision
        )

    async def get_current(self, claim_event_id: str) -> ReconciliationResult:
        return await self._repository.get_reconciliation_result(claim_event_id)
