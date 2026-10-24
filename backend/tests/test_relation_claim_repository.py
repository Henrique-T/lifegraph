"""Repository-level C2 transaction and graph-shape tests."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from neo4j.exceptions import Neo4jError

from app.domain.enums import Origin, VerificationStatus
from app.graph.client import SCHEMA_STATEMENTS
from app.graph.repository import DomainNotFoundError, DomainPersistenceError, GraphRepository
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


NOW = datetime(2026, 1, 1, tzinfo=UTC)
SOURCE = "João é pai de Maria."


def claim(**changes: object) -> RelationClaim:
    values: dict[str, object] = {
        "relation_claim_id": "claim-1", "relation_type": RelationType.FATHER_OF,
        "relation_surface_text": "pai de", "source_text": SOURCE, "source_reference": "source-1",
        "polarity": RelationPolarity.POSITIVE, "epistemic_status": EpistemicStatus.ASSERTED,
        "reporting_mode": ReportingMode.DIRECT,
        "temporal_scope": RelationTemporalScope.CURRENT_OR_UNSPECIFIED,
        "origin": Origin.CONVERSATION, "verification_status": VerificationStatus.DECLARED,
        "endpoint_a_person_id": "person-a", "endpoint_b_person_id": "person-b",
        "conversation_turn_id": "turn-1", "original_relation_surface": "pai de",
        "original_endpoint_a_mention": "João", "original_endpoint_b_mention": "Maria",
        "accepted_relation_surface": "pai de", "accepted_endpoint_a_mention": "João",
        "accepted_endpoint_b_mention": "Maria", "accepted_relation_span_start": 7,
        "accepted_relation_span_end": 13, "accepted_endpoint_a_span_start": 0,
        "accepted_endpoint_a_span_end": 4, "accepted_endpoint_b_span_start": 14,
        "accepted_endpoint_b_span_end": 19,
        "endpoint_a_semantic_target": EndpointSemanticTarget.EXPLICIT_MENTION,
        "endpoint_b_semantic_target": EndpointSemanticTarget.EXPLICIT_MENTION,
        "reviewer_correction_applied": False, "reviewer_corrections_json": "{}",
        "extraction_id": "review-1", "candidate_id": "candidate-1",
        "pipeline_id": "LIFEGRAPH_PERSON_RELATION_V1",
        "model_id": "deterministic-structural-baseline", "model_revision": "A0_B2+B3+B4",
        "configuration_hash": "32040A53D33F30A4DDDBA0E423180AB9DC08AF17B583BB6B3A9A82BEA091FC7D",
        "acceptance_payload_hash": "acceptance-hash", "persistence_operation_key": "operation-key",
        "review_id": "review-1", "reviewed_at": NOW, "accepted_at": NOW,
        "canonical_relation_family": CanonicalRelationFamily.PARENT_CHILD,
        "canonical_pair_key": canonical_pair_key(RelationType.FATHER_OF, "person-a", "person-b"),
        "created_at": NOW,
    }
    values.update(changes)
    return RelationClaim.model_validate(values)


def row(value: RelationClaim, *, created: bool = True):
    return {
        "claim": value.model_dump(mode="json"),
        "endpoint_a": {"person_id": "person-a", "display_name": "A", "created_at": NOW.isoformat(), "external_ref_person_id": None},
        "endpoint_b": {"person_id": "person-b", "display_name": "B", "created_at": NOW.isoformat(), "external_ref_person_id": None},
        "conversation_turn": {
            "conversation_turn_id": "turn-1", "text": SOURCE, "speaker": "USER",
            "created_at": NOW.isoformat(), "review_extraction_id": "review-1",
        },
        "created": created,
    }


@pytest.mark.anyio
async def test_persistence_is_one_atomic_query_with_three_role_edges() -> None:
    driver = AsyncMock()
    value = claim()
    driver.execute_query.return_value = ([row(value)], None, None)
    graph, created = await GraphRepository(driver).persist_relation_claim(value)
    query = driver.execute_query.await_args.args[0]
    assert driver.execute_query.await_count == 1
    assert "[:ENDPOINT_A]" in query and "[:ENDPOINT_B]" in query
    assert "[:EXTRACTED_FROM]" in query
    assert "FATHER_OF]->" not in query and "SPOUSE_OF]->" not in query
    assert graph.claim.relation_claim_id == "claim-1" and created is True


@pytest.mark.anyio
async def test_missing_endpoint_or_turn_causes_no_claim_result() -> None:
    driver = AsyncMock()
    driver.execute_query.return_value = ([], None, None)
    with pytest.raises(DomainNotFoundError):
        await GraphRepository(driver).persist_relation_claim(claim())
    assert driver.execute_query.await_count == 1


@pytest.mark.anyio
@pytest.mark.parametrize("failure_stage", ["claim", "endpoint_a", "endpoint_b", "provenance", "commit"])
async def test_single_transaction_failure_never_returns_partial_state(failure_stage: str) -> None:
    driver = AsyncMock()
    driver.execute_query.side_effect = Neo4jError(f"injected-{failure_stage}")
    with pytest.raises(DomainPersistenceError):
        await GraphRepository(driver).persist_relation_claim(claim())
    assert driver.execute_query.await_count == 1


@pytest.mark.anyio
async def test_readback_requires_complete_endpoint_and_provenance_shape() -> None:
    driver = AsyncMock()
    value = claim()
    complete = row(value)
    complete.pop("created")
    driver.execute_query.return_value = ([complete], None, None)
    graph = await GraphRepository(driver).get_relation_claim_graph("claim-1")
    query = driver.execute_query.await_args.args[0]
    assert "ENDPOINT_A" in query and "ENDPOINT_B" in query and "EXTRACTED_FROM" in query
    assert graph.endpoint_a.person_id == "person-a"
    assert graph.endpoint_b.person_id == "person-b"
    assert graph.conversation_turn.conversation_turn_id == "turn-1"


def test_schema_has_only_id_and_operation_uniqueness_for_relation_claim() -> None:
    relation_statements = [item for item in SCHEMA_STATEMENTS if "RelationClaim" in item]
    assert any("relation_claim_id" in item and "UNIQUE" in item for item in relation_statements)
    assert any("persistence_operation_key" in item and "UNIQUE" in item for item in relation_statements)
    assert not any("canonical_pair_key" in item and "UNIQUE" in item for item in relation_statements)
