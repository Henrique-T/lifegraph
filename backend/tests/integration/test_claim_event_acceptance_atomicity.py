"""Live Neo4j rollback checks for atomic ClaimEvent acceptance."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.core.config import get_settings
from app.domain.enums import Speaker
from app.domain.schemas import ClaimEventCreate, PersonCreate
from app.extraction.schemas import ReviewCandidate
from app.graph.client import Neo4jClient
from app.graph.repository import DomainConflictError, GraphRepository


class RollbackAfterQueryDriver:
    """Execute the production query, then inject failure before commit."""

    def __init__(self, driver) -> None:
        self._driver = driver

    async def execute_query(self, query: str, **parameters):
        async with self._driver.session() as session:
            transaction = await session.begin_transaction()
            try:
                result = await transaction.run(query, **parameters)
                await result.consume()
                raise RuntimeError("INJECTED_BEFORE_COMMIT")
            finally:
                await transaction.rollback()


def candidate() -> ReviewCandidate:
    return ReviewCandidate(
        candidate_id="candidate-1",
        event_type="casamento",
        trigger_text="se casou",
        trigger_start=5,
        trigger_end=13,
        subject_text="Atomic Person",
        subject_resolution="RESOLVED",
        subject_reason="EXPLICIT_PRETRIGGER_SUBJECT",
        participant_texts=[],
        date_expression="2019",
        normalized_time_candidate={
            "start": datetime(2019, 1, 1, tzinfo=UTC),
            "end": datetime(2019, 12, 31, 23, 59, 59, tzinfo=UTC),
            "temporal_precision": "YEAR",
            "normalization_method": "DETERMINISTIC_YEAR_PATTERN",
        },
        warnings=[],
    )


async def accept(repository: GraphRepository, person_id: str, extraction_id: str):
    return await repository.accept_extraction_candidate(
        person_id=person_id,
        source_text="João se casou em 2019.",
        extraction_id=extraction_id,
        candidate_id="candidate-1",
        pipeline_id="LIFEGRAPH_PT_CIVIL_V1",
        model_id="fastino/gliner2.5-multi-v1",
        model_revision="aaecfe45db1d828c963717054ccb868e8ad1f1d5",
        candidate=candidate(),
        claim=ClaimEventCreate(
            event_type="casamento",
            claimed_date_start=datetime(2019, 1, 1, tzinfo=UTC),
            claimed_date_end=datetime(2019, 12, 31, 23, 59, 59, tzinfo=UTC),
            temporal_precision="YEAR",
        ),
        correction_data={},
        payload_hash=f"payload-{extraction_id}",
        speaker=Speaker.USER,
    )


@pytest.mark.integration
def test_claim_event_acceptance_is_complete_or_fully_rolled_back() -> None:
    asyncio.run(_run())


async def _run() -> None:
    client = Neo4jClient(get_settings())
    await client.initialize_schema()
    repository = GraphRepository(client.driver)
    suffix = str(uuid4())
    person = None
    extraction_ids = [f"atomic-success-{suffix}", f"atomic-missing-{suffix}", f"atomic-rollback-{suffix}"]
    try:
        person = await repository.create_person(PersonCreate(display_name=f"Atomic Person {suffix}"))

        successful = await accept(repository, person.person_id, extraction_ids[0])
        records, _, _ = await client.driver.execute_query(
            """
            MATCH (claim:ClaimEvent {claim_event_id: $claim_id})
            RETURN claim.origin AS origin,
                   claim.verification_status AS status,
                   count { (:Person)-[:SUBJECT_OF]->(claim) } AS subjects,
                   count { (claim)-[:EXTRACTED_FROM]->(:ConversationTurn) } AS sources,
                   count { (claim)-[:SUPPORTED_BY|CONTRADICTS]->() } AS reconciliation_edges
            """,
            claim_id=successful["claim_event_id"],
        )
        complete = records[0]
        assert complete["origin"] == "CONVERSATION"
        assert complete["status"] == "DECLARED"
        assert complete["subjects"] == complete["sources"] == 1
        assert complete["reconciliation_edges"] == 0

        with pytest.raises(DomainConflictError):
            await accept(repository, f"missing-{suffix}", extraction_ids[1])

        rollback_repository = GraphRepository(RollbackAfterQueryDriver(client.driver))
        with pytest.raises(RuntimeError, match="INJECTED_BEFORE_COMMIT"):
            await accept(rollback_repository, person.person_id, extraction_ids[2])

        partial, _, _ = await client.driver.execute_query(
            """
            MATCH (n)
            WHERE n.review_extraction_id IN $failed_ids
               OR n.extraction_id IN $failed_ids
            RETURN labels(n) AS labels, count(n) AS count
            """,
            failed_ids=extraction_ids[1:],
        )
        assert partial == []
    finally:
        await client.driver.execute_query(
            """
            MATCH (n)
            WHERE n.person_id = $person_id
               OR n.review_extraction_id IN $extraction_ids
               OR n.extraction_id IN $extraction_ids
            DETACH DELETE n
            """,
            person_id=person.person_id if person else "",
            extraction_ids=extraction_ids,
        )
        await client.close()
