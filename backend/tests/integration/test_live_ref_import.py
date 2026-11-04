"""Opt-in integration test for a live REF trail import."""

import asyncio
import os
from uuid import UUID, uuid4

import pytest

from app.core.config import get_settings
from app.domain.schemas import ClaimEventCreate, PersonCreate
from app.graph.client import Neo4jClient
from app.graph.repository import GraphRepository
from app.ref.client import RefClient
from app.ref.service import RefImportService


@pytest.mark.integration
def test_live_ref_import_is_idempotent_and_does_not_reconcile() -> None:
    """Verify live ref import is idempotent and does not reconcile."""
    ref_person_id = os.getenv("LIVE_REF_PERSON_ID")
    if not ref_person_id or not os.getenv("REF_BEARER_TOKEN"):
        pytest.skip("LIVE_REF_PERSON_ID and REF_BEARER_TOKEN are required")
    asyncio.run(_run(UUID(ref_person_id)))


async def _run(ref_person_id: UUID) -> None:
    """Run the asynchronous test scenario."""
    graph = Neo4jClient(get_settings())
    await graph.initialize_schema()
    repository = GraphRepository(graph.driver)
    ref_client = RefClient(get_settings())
    person = None
    claim = None
    imported_external_ids: list[str] = []
    try:
        person = await repository.create_person(
            PersonCreate(display_name=f"Live REF integration {uuid4()}")
        )
        claim = await repository.create_claim_event(
            ClaimEventCreate(event_type="nascimento")
        )
        service = RefImportService(ref_client, repository)
        first = await service.import_person_trail(person.person_id, ref_person_id)
        second = await service.import_person_trail(person.person_id, ref_person_id)
        assert first.retrieved_events > 0
        assert first.created_events > 0
        assert second.created_events == 0
        assert second.existing_events == first.created_events

        imported_external_ids = [
            str(item.id_ato)
            for item in await ref_client.get_person_trail(ref_person_id)
            if item.tipo in {"nascimento", "casamento", "obito", "natimorto"}
        ]
        records, _, _ = await graph.driver.execute_query(
            """
            MATCH (person:Person {person_id: $person_id})-[p:PARTICIPATES_IN]->(:RefEvent)
            MATCH (claim:ClaimEvent {claim_event_id: $claim_id})
            RETURN collect(p.role) AS roles,
                   claim.verification_status AS status,
                   count { (claim)-[:SUPPORTED_BY]->(:RefEvent) } AS supported,
                   count { (claim)-[:CONTRADICTS]->(:RefEvent) } AS contradicted
            """,
            person_id=person.person_id,
            claim_id=claim.claim_event_id,
        )
        result = records[0]
        assert result["roles"]
        assert result["status"] == "DECLARED"
        assert result["supported"] == 0
        assert result["contradicted"] == 0
    finally:
        await graph.driver.execute_query(
            """
            MATCH (n)
            WHERE n.person_id = $person_id
               OR n.claim_event_id = $claim_id
               OR n.external_ref_id IN $external_ids
            DETACH DELETE n
            """,
            person_id=person.person_id if person else "",
            claim_id=claim.claim_event_id if claim else "",
            external_ids=imported_external_ids,
        )
        await ref_client.close()
        await graph.close()
