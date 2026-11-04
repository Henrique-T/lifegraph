"""Integration tests for reconciliation persistence and isolation."""

import asyncio
from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.core.config import get_settings
from app.domain.schemas import ClaimEventCreate, PersonCreate, RefEventCreate
from app.graph.client import Neo4jClient
from app.graph.repository import GraphRepository
from app.reconciliation.engine import ReconciliationEngine
from app.reconciliation.schemas import ReasonCode

UTC = timezone.utc


@pytest.mark.integration
def test_reconciliation_persistence_refresh_and_cross_person_isolation() -> None:
    """Verify reconciliation persistence refresh and cross person isolation."""
    asyncio.run(_run())


async def _run() -> None:
    """Run the asynchronous test scenario."""
    client = Neo4jClient(get_settings())
    await client.initialize_schema()
    repository = GraphRepository(client.driver)
    engine = ReconciliationEngine(repository)
    object_ids: list[str] = []
    claim_ids: list[str] = []
    suffix = str(uuid4())

    async def new_person(name: str):
        """Create a person for the scenario."""
        item = await repository.create_person(PersonCreate(display_name=name))
        object_ids.append(item.person_id)
        return item

    async def new_claim(person, year: int):
        """Create a claim for the scenario."""
        item = await repository.create_claim_event(
            ClaimEventCreate(
                event_type="casamento",
                claimed_date_start=datetime(year, 1, 1, tzinfo=UTC),
                claimed_date_end=datetime(year, 12, 31, 23, 59, 59, tzinfo=UTC),
                temporal_precision="YEAR",
            )
        )
        object_ids.append(item.claim_event_id)
        claim_ids.append(item.claim_event_id)
        await repository.link_person_claim(person.person_id, item.claim_event_id)
        return item

    async def new_ref(person, label: str, year: int):
        """Create a ref for the scenario."""
        item = await repository.create_ref_event(
            RefEventCreate(
                external_ref_id=f"reconciliation-{suffix}-{label}",
                event_type="casamento",
                event_date=datetime(year, 6, 15, tzinfo=UTC),
                registration_date=datetime(year, 6, 16, tzinfo=UTC),
            )
        )
        object_ids.append(item.ref_event_id)
        await repository.link_person_ref_event(person.person_id, item.ref_event_id, "nubente")
        return item

    try:
        person_a = await new_person("Reconciliation A")
        claim_a = await new_claim(person_a, 2019)
        ref_a = await new_ref(person_a, "a", 2019)

        first = await engine.reconcile(claim_a.claim_event_id)
        assert first.status.value == "CONFIRMED"
        assert first.matched_ref_event_id == ref_a.ref_event_id
        persisted_claim = await repository.get_claim_event(claim_a.claim_event_id)
        assert persisted_claim.origin.value == "CONVERSATION"
        assert persisted_claim.verification_status.value == "CONFIRMED"

        before, _, _ = await client.driver.execute_query(
            """
            MATCH (e:Evidence {source: 'RECONCILIATION_ENGINE'})-[:ABOUT]->
                  (:ClaimEvent {claim_event_id: $claim_id})
            OPTIONAL MATCH (claim:ClaimEvent {claim_event_id: $claim_id})-[r:SUPPORTED_BY]->()
            RETURN collect(DISTINCT e.evidence_id) AS evidence_ids,
                   count(DISTINCT r) AS edge_count
            """,
            claim_id=claim_a.claim_event_id,
        )
        second = await engine.reconcile(claim_a.claim_event_id)
        after, _, _ = await client.driver.execute_query(
            """
            MATCH (e:Evidence {source: 'RECONCILIATION_ENGINE'})-[:ABOUT]->
                  (:ClaimEvent {claim_event_id: $claim_id})
            OPTIONAL MATCH (claim:ClaimEvent {claim_event_id: $claim_id})-[r:SUPPORTED_BY]->()
            RETURN collect(DISTINCT e.evidence_id) AS evidence_ids,
                   count(DISTINCT r) AS edge_count
            """,
            claim_id=claim_a.claim_event_id,
        )
        assert second.status.value == "CONFIRMED"
        assert before[0]["evidence_ids"] == after[0]["evidence_ids"]
        assert before[0]["edge_count"] == after[0]["edge_count"] == 1

        await new_ref(person_a, "a-second", 2019)
        refreshed = await engine.reconcile(claim_a.claim_event_id)
        assert refreshed.status.value == "UNVERIFIED"
        assert ReasonCode.AMBIGUOUS_MULTIPLE_REF_CANDIDATES in refreshed.reason_codes
        stale, _, _ = await client.driver.execute_query(
            """
            MATCH (claim:ClaimEvent {claim_event_id: $claim_id})
            OPTIONAL MATCH (claim)-[r:SUPPORTED_BY|CONTRADICTS]->()
            OPTIONAL MATCH (e:Evidence {source: 'RECONCILIATION_ENGINE'})-[:ABOUT]->(claim)
            RETURN count(DISTINCT r) AS reconciliation_edges,
                   collect(DISTINCT e.evidence_type) AS evidence_types
            """,
            claim_id=claim_a.claim_event_id,
        )
        assert stale[0]["reconciliation_edges"] == 0
        assert set(stale[0]["evidence_types"]) == {
            "EVENT_TYPE_MATCH",
            "AMBIGUOUS_MULTIPLE_REF_CANDIDATES",
        }

        person_b = await new_person("Reconciliation B")
        await new_ref(person_b, "cross-person", 2019)
        person_c = await new_person("Reconciliation C")
        cross_claim = await new_claim(person_c, 2019)
        cross = await engine.reconcile(cross_claim.claim_event_id)
        assert cross.status.value == "UNVERIFIED"
        assert cross.reason_codes == [ReasonCode.NO_MATCHING_REF_EVENT_TYPE]

        person_d = await new_person("Reconciliation D")
        claim_d = await new_claim(person_d, 2010)
        ref_d = await new_ref(person_d, "divergent", 2019)
        divergent = await engine.reconcile(claim_d.claim_event_id)
        assert divergent.status.value == "DIVERGENT"
        assert divergent.matched_ref_event_id is None
        edges, _, _ = await client.driver.execute_query(
            """
            MATCH (:ClaimEvent {claim_event_id: $claim_id})-[r:CONTRADICTS]->
                  (:RefEvent {ref_event_id: $ref_id})
            RETURN count(r) AS count
            """,
            claim_id=claim_d.claim_event_id,
            ref_id=ref_d.ref_event_id,
        )
        assert edges[0]["count"] == 1
    finally:
        await client.driver.execute_query(
            """
            MATCH (e:Evidence {source: 'RECONCILIATION_ENGINE'})
            WHERE any(id IN $claim_ids WHERE e.evidence_key STARTS WITH 'reconciliation:' + id + ':')
            DETACH DELETE e
            """,
            claim_ids=claim_ids,
        )
        await client.driver.execute_query(
            """
            MATCH (n)
            WHERE coalesce(n.person_id, n.claim_event_id, n.ref_event_id, '') IN $ids
            DETACH DELETE n
            """,
            ids=object_ids,
        )
        await client.close()
