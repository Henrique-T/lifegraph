"""Live Neo4j integration checks for atomic RelationClaim persistence."""

import asyncio
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.core.config import get_settings
from app.domain.enums import Origin, VerificationStatus
from app.domain.schemas import PersonCreate
from app.graph.client import Neo4jClient
from app.graph.repository import DomainNotFoundError, GraphRepository
from app.relations.canonical import canonical_pair_key
from app.relations.enums import (
    CanonicalRelationFamily,
    EndpointSemanticTarget,
    EpistemicStatus,
    RelationPolarity,
    RelationTemporalScope,
    RelationType,
    ReportingMode,
)
from app.relations.schemas import RelationClaim


@pytest.mark.integration
def test_relation_claim_atomic_idempotent_and_independent() -> None:
    asyncio.run(_run_scenario())


async def _run_scenario() -> None:
    client = Neo4jClient(get_settings())
    await client.initialize_schema()
    repository = GraphRepository(client.driver)
    suffix = str(uuid4())
    person_ids: list[str] = []
    turn_ids: list[str] = []
    claim_ids: list[str] = []
    try:
        endpoint_a = await repository.create_person(PersonCreate(display_name=f"C2 A {suffix}"))
        endpoint_b = await repository.create_person(PersonCreate(display_name=f"C2 B {suffix}"))
        person_ids.extend([endpoint_a.person_id, endpoint_b.person_id])
        turns = []
        for index in (1, 2):
            turns.append(await repository.ensure_relation_review_turn(
                review_id=f"c2-review-{suffix}-{index}",
                source_text="João é pai de Maria.",
            ))
        turn_ids.extend(turn.conversation_turn_id for turn in turns)

        def make_claim(index: int) -> RelationClaim:
            now = datetime.now(UTC)
            claim_id = f"c2-claim-{suffix}-{index}"
            claim_ids.append(claim_id)
            return RelationClaim(
                relation_claim_id=claim_id, relation_type=RelationType.FATHER_OF,
                relation_surface_text="pai de", source_text="João é pai de Maria.",
                source_reference=f"source-{index}", polarity=RelationPolarity.POSITIVE,
                epistemic_status=EpistemicStatus.ASSERTED, reporting_mode=ReportingMode.DIRECT,
                temporal_scope=RelationTemporalScope.CURRENT_OR_UNSPECIFIED,
                origin=Origin.CONVERSATION, verification_status=VerificationStatus.DECLARED,
                endpoint_a_person_id=endpoint_a.person_id, endpoint_b_person_id=endpoint_b.person_id,
                conversation_turn_id=turns[index - 1].conversation_turn_id,
                original_relation_surface="pai de", original_endpoint_a_mention="João",
                original_endpoint_b_mention="Maria", accepted_relation_surface="pai de",
                accepted_endpoint_a_mention="João", accepted_endpoint_b_mention="Maria",
                accepted_relation_span_start=7, accepted_relation_span_end=13,
                accepted_endpoint_a_span_start=0, accepted_endpoint_a_span_end=4,
                accepted_endpoint_b_span_start=14, accepted_endpoint_b_span_end=19,
                endpoint_a_semantic_target=EndpointSemanticTarget.EXPLICIT_MENTION,
                endpoint_b_semantic_target=EndpointSemanticTarget.EXPLICIT_MENTION,
                reviewer_correction_applied=False, reviewer_corrections_json="{}",
                extraction_id=f"c2-review-{suffix}-{index}", candidate_id="candidate-1",
                pipeline_id="LIFEGRAPH_PERSON_RELATION_V1",
                model_id="deterministic-structural-baseline", model_revision="A0_B2+B3+B4",
                configuration_hash="32040A53D33F30A4DDDBA0E423180AB9DC08AF17B583BB6B3A9A82BEA091FC7D",
                acceptance_payload_hash=f"accepted-{suffix}-{index}",
                persistence_operation_key=f"operation-{suffix}-{index}",
                review_id=f"c2-review-{suffix}-{index}", reviewed_at=now, accepted_at=now,
                canonical_relation_family=CanonicalRelationFamily.PARENT_CHILD,
                canonical_pair_key=canonical_pair_key(
                    RelationType.FATHER_OF, endpoint_a.person_id, endpoint_b.person_id
                ),
                created_at=now,
            )

        first_claim = make_claim(1)
        first, created = await repository.persist_relation_claim(first_claim)
        replay, replay_created = await repository.persist_relation_claim(first_claim)
        second, second_created = await repository.persist_relation_claim(make_claim(2))
        assert created is True and replay_created is False and second_created is True
        assert first.claim.relation_claim_id == replay.claim.relation_claim_id
        assert first.claim.relation_claim_id != second.claim.relation_claim_id
        assert first.claim.canonical_pair_key == second.claim.canonical_pair_key

        records, _, _ = await client.driver.execute_query(
            """
            MATCH (claim:RelationClaim)
            WHERE claim.relation_claim_id IN $claim_ids
            RETURN count(claim) AS claims,
                   sum(count { (claim)-[:ENDPOINT_A]->(:Person) }) AS endpoint_a,
                   sum(count { (claim)-[:ENDPOINT_B]->(:Person) }) AS endpoint_b,
                   sum(count { (claim)-[:EXTRACTED_FROM]->(:ConversationTurn) }) AS provenance,
                   sum(count { (:Person)-[:FATHER_OF|MOTHER_OF|SON_OF|DAUGHTER_OF|BROTHER_OF|SISTER_OF|SPOUSE_OF]->(:Person) }) AS direct_facts
            """,
            claim_ids=claim_ids,
        )
        counts = records[0]
        assert counts["claims"] == 2
        assert counts["endpoint_a"] == counts["endpoint_b"] == counts["provenance"] == 2
        assert counts["direct_facts"] == 0

        graph = await repository.get_graph()
        relation_nodes = [node for node in graph.nodes if node.id in claim_ids]
        relation_edges = [
            edge for edge in graph.edges
            if edge.source in claim_ids and edge.type in {"ENDPOINT_A", "ENDPOINT_B", "EXTRACTED_FROM"}
        ]
        assert len(relation_nodes) == 2
        assert all(node.type == "RelationClaim" for node in relation_nodes)
        assert len(relation_edges) == 6

        missing = make_claim(1).model_copy(update={
            "relation_claim_id": f"missing-turn-{suffix}",
            "conversation_turn_id": "missing-turn",
            "persistence_operation_key": f"missing-operation-{suffix}",
        })
        claim_ids.append(missing.relation_claim_id)
        with pytest.raises(DomainNotFoundError):
            await repository.persist_relation_claim(missing)
        absent, _, _ = await client.driver.execute_query(
            "MATCH (claim:RelationClaim {relation_claim_id: $claim_id}) RETURN count(claim) AS count",
            claim_id=missing.relation_claim_id,
        )
        assert absent[0]["count"] == 0
    finally:
        await client.driver.execute_query(
            """
            MATCH (n)
            WHERE n.person_id IN $person_ids
               OR n.conversation_turn_id IN $turn_ids
               OR n.relation_claim_id IN $claim_ids
            DETACH DELETE n
            """,
            person_ids=person_ids,
            turn_ids=turn_ids,
            claim_ids=claim_ids,
        )
        await client.close()
