"""Repository contract tests for atomic ClaimEvent acceptance."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from neo4j.exceptions import Neo4jError

from app.domain.enums import Speaker
from app.domain.schemas import ClaimEventCreate
from app.extraction.schemas import ReviewCandidate
from app.graph.repository import (
    DomainConflictError,
    DomainPersistenceError,
    GraphRepository,
)


def candidate() -> ReviewCandidate:
    return ReviewCandidate(
        candidate_id="candidate-1",
        event_type="casamento",
        trigger_text="me casei",
        trigger_start=3,
        trigger_end=11,
        subject_text="__NARRATOR__",
        subject_resolution="RESOLVED",
        subject_reason="EXPLICIT_FIRST_PERSON_PRONOUN",
        participant_texts=["Ana"],
        date_expression="2019",
        normalized_time_candidate={
            "start": datetime(2019, 1, 1, tzinfo=UTC),
            "end": datetime(2019, 12, 31, 23, 59, 59, tzinfo=UTC),
            "temporal_precision": "YEAR",
            "normalization_method": "DETERMINISTIC_YEAR_PATTERN",
        },
        warnings=[],
    )


async def accept(repository: GraphRepository):
    return await repository.accept_extraction_candidate(
        person_id="person-1",
        source_text="Eu me casei com Ana em 2019.",
        extraction_id="extraction-1",
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
        payload_hash="payload-hash",
        speaker=Speaker.USER,
    )


@pytest.mark.anyio
async def test_acceptance_is_one_atomic_query_with_complete_provenance() -> None:
    driver = AsyncMock()
    driver.execute_query.return_value = ([{
        "claim_event_id": "claim-1",
        "conversation_turn_id": "turn-1",
        "stored_payload_hash": "payload-hash",
        "created": True,
    }], None, None)

    result = await accept(GraphRepository(driver))

    assert driver.execute_query.await_count == 1
    query = driver.execute_query.await_args.args[0]
    assert "MERGE (claim:ClaimEvent" in query
    assert "MERGE (turn:ConversationTurn" in query
    assert "MERGE (person)-[:SUBJECT_OF]->(claim)" in query
    assert "MERGE (claim)-[:EXTRACTED_FROM]->(turn)" in query
    assert result["origin"] == "CONVERSATION"
    assert result["verification_status"] == "DECLARED"


@pytest.mark.anyio
async def test_missing_person_returns_no_acceptance_result() -> None:
    driver = AsyncMock()
    driver.execute_query.return_value = ([], None, None)

    with pytest.raises(DomainConflictError):
        await accept(GraphRepository(driver))
    assert driver.execute_query.await_count == 1


@pytest.mark.anyio
async def test_database_failure_returns_no_partial_acceptance_result() -> None:
    driver = AsyncMock()
    driver.execute_query.side_effect = Neo4jError("injected transaction failure")

    with pytest.raises(DomainPersistenceError):
        await accept(GraphRepository(driver))
    assert driver.execute_query.await_count == 1
