import asyncio
from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.core.config import get_settings
from app.domain.schemas import (
    ClaimEventCreate,
    ConversationTurnCreate,
    EvidenceCreate,
    PersonCreate,
    RefEventCreate,
)
from app.graph.client import Neo4jClient
from app.graph.repository import DomainConflictError, GraphRepository


@pytest.mark.integration
def test_complete_persistence_and_safety_scenario() -> None:
    asyncio.run(_run_scenario())


async def _run_scenario() -> None:
    client = Neo4jClient(get_settings())
    await client.initialize_schema()
    repository = GraphRepository(client.driver)
    suffix = str(uuid4())
    ids: list[str] = []

    try:
        person = await repository.create_person(PersonCreate(display_name="Test Person"))
        turn = await repository.create_conversation_turn(
            ConversationTurnCreate(text="Eu me casei em 2019.", speaker="USER")
        )
        claim = await repository.create_claim_event(
            ClaimEventCreate(event_type="casamento")
        )
        ref_event = await repository.create_ref_event(
            RefEventCreate(
                external_ref_id=f"integration-ref-{suffix}",
                event_type="casamento",
                registration_date=datetime.now(timezone.utc),
            )
        )
        evidence = await repository.create_evidence(
            EvidenceCreate(
                evidence_type="integration-test",
                description="Task-scoped persistence test evidence",
            )
        )
        ids.extend(
            [
                person.person_id,
                turn.conversation_turn_id,
                claim.claim_event_id,
                ref_event.ref_event_id,
                evidence.evidence_id,
            ]
        )

        assert (await repository.get_person(person.person_id)) == person
        assert (await repository.get_conversation_turn(turn.conversation_turn_id)) == turn
        assert (await repository.get_claim_event(claim.claim_event_id)) == claim
        assert (await repository.get_ref_event(ref_event.ref_event_id)) == ref_event
        assert (await repository.get_evidence(evidence.evidence_id)) == evidence

        await repository.link_person_claim(person.person_id, claim.claim_event_id)
        await repository.link_claim_source(claim.claim_event_id, turn.conversation_turn_id)
        await repository.link_person_ref_event(
            person.person_id, ref_event.ref_event_id, "principal"
        )
        await repository.link_evidence_claim(evidence.evidence_id, claim.claim_event_id)
        await repository.link_evidence_ref_event(evidence.evidence_id, ref_event.ref_event_id)

        safety_records, _, _ = await client.driver.execute_query(
            """
            MATCH (claim:ClaimEvent {claim_event_id: $claim_id})
            MATCH (ref:RefEvent {ref_event_id: $ref_id})
            RETURN claim.verification_status AS status,
                   count { (claim)-[:SUPPORTED_BY]->(ref) } AS supported,
                   count { (claim)-[:CONTRADICTS]->(ref) } AS contradicted
            """,
            claim_id=claim.claim_event_id,
            ref_id=ref_event.ref_event_id,
        )
        safety = safety_records[0]
        assert safety["status"] == "DECLARED"
        assert safety["supported"] == 0
        assert safety["contradicted"] == 0

        graph = await repository.get_graph()
        graph_ids = {node.id for node in graph.nodes}
        assert set(ids).issubset(graph_ids)
        graph_relationships = {edge.type for edge in graph.edges}
        assert {
            "SUBJECT_OF",
            "EXTRACTED_FROM",
            "PARTICIPATES_IN",
            "ABOUT",
            "DERIVED_FROM",
        }.issubset(graph_relationships)

        with pytest.raises(DomainConflictError):
            await repository.create_ref_event(
                RefEventCreate(
                    external_ref_id=ref_event.external_ref_id,
                    event_type="casamento",
                    registration_date=datetime.now(timezone.utc),
                )
            )

        supported = await repository.link_claim_ref_event(
            claim.claim_event_id, ref_event.ref_event_id, "SUPPORTED_BY"
        )
        contradicted = await repository.link_claim_ref_event(
            claim.claim_event_id, ref_event.ref_event_id, "CONTRADICTS"
        )
        assert supported.relationship == "SUPPORTED_BY"
        assert contradicted.relationship == "CONTRADICTS"
        assert (await repository.get_claim_event(claim.claim_event_id)).verification_status.value == "DECLARED"
    finally:
        if ids:
            await client.driver.execute_query(
                """
                MATCH (n)
                WHERE coalesce(
                  n.person_id, n.claim_event_id, n.ref_event_id,
                  n.conversation_turn_id, n.evidence_id
                ) IN $ids
                DETACH DELETE n
                """,
                ids=ids,
            )
        await client.close()
