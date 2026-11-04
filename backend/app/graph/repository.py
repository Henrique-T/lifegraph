"""Neo4j persistence operations for LifeGraph domain entities."""

import json
import logging
from datetime import datetime, timezone
from typing import Any, TypeVar
from uuid import uuid4

from neo4j import AsyncDriver
from neo4j.exceptions import ConstraintError, Neo4jError
from pydantic import BaseModel

from app.domain.schemas import (
    ClaimEventCreate,
    ClaimEventRead,
    ConversationTurnCreate,
    ConversationTurnRead,
    EvidenceCreate,
    EvidenceRead,
    GraphEdge,
    GraphNode,
    GraphRead,
    PersonCreate,
    PersonRead,
    RefEventCreate,
    RefEventRead,
    RelationshipRead,
)
from app.extraction.schemas import ReviewCandidate
from app.reconciliation.schemas import (
    ReasonCode,
    ReconciliationDecision,
    ReconciliationResult,
)
from app.relations.schemas import RelationClaim, RelationClaimGraphRead

logger = logging.getLogger(__name__)
ReadModel = TypeVar("ReadModel", bound=BaseModel)
RECONCILIATION_SOURCE = "RECONCILIATION_ENGINE"

REASON_DESCRIPTIONS = {
    ReasonCode.NO_MATCHING_REF_EVENT_TYPE: "No same-type REF event exists for the linked person.",
    ReasonCode.EVENT_TYPE_MATCH: "The claim and candidate REF event types are equal.",
    ReasonCode.EVENT_DATE_WITHIN_CLAIM_INTERVAL: "The REF event date is inside the claimed interval.",
    ReasonCode.EVENT_DATE_OUTSIDE_CLAIM_INTERVAL: "The REF event date is outside the claimed interval.",
    ReasonCode.INSUFFICIENT_TEMPORAL_EVIDENCE: "The claim interval or a required REF event date is unavailable.",
    ReasonCode.UNIQUE_TEMPORALLY_COMPATIBLE_CANDIDATE: "Exactly one same-type REF event is temporally compatible.",
    ReasonCode.NO_TEMPORALLY_COMPATIBLE_REF_EVENT: "No dated same-type REF event is inside the claimed interval.",
    ReasonCode.AMBIGUOUS_MULTIPLE_REF_CANDIDATES: "More than one same-type REF event is temporally compatible.",
}


class DomainNotFoundError(Exception):
    """Raised when a requested graph entity does not exist."""


class DomainConflictError(Exception):
    """Raised when a write conflicts with existing domain state."""


class DomainPersistenceError(Exception):
    """Raised when Neo4j cannot complete a persistence operation."""


def _new_id() -> str:
    """Generate an application-owned UUID identifier."""
    return str(uuid4())


def _utc_now() -> str:
    """Return the current UTC timestamp in ISO 8601 format."""
    return datetime.now(timezone.utc).isoformat()


class GraphRepository:
    """Persist and retrieve LifeGraph nodes and relationships."""

    def __init__(self, driver: AsyncDriver) -> None:
        """Initialize the repository with a Neo4j driver."""
        self._driver = driver

    async def _create_node(
        self,
        *,
        label: str,
        id_field: str,
        values: dict[str, Any],
        read_model: type[ReadModel],
    ) -> ReadModel:
        """Create a validated node and return its properties."""
        properties = {id_field: _new_id(), "created_at": _utc_now(), **values}
        query = f"CREATE (n:{label} $properties) RETURN properties(n) AS node"
        try:
            records, _, _ = await self._driver.execute_query(
                query, properties=properties
            )
        except ConstraintError as exc:
            logger.warning("Domain uniqueness conflict for label=%s", label)
            raise DomainConflictError(f"{label} already exists") from exc
        except Neo4jError as exc:
            logger.exception("Persistence error creating label=%s", label)
            raise DomainPersistenceError("Graph persistence failed") from exc
        logger.info("Domain node created label=%s id=%s", label, properties[id_field])
        return read_model.model_validate(records[0]["node"])

    async def _get_node(
        self,
        *,
        label: str,
        id_field: str,
        object_id: str,
        read_model: type[ReadModel],
    ) -> ReadModel:
        """Read one node by its application identifier."""
        query = (
            f"MATCH (n:{label} {{{id_field}: $object_id}}) "
            "RETURN properties(n) AS node"
        )
        records, _, _ = await self._driver.execute_query(query, object_id=object_id)
        if not records:
            raise DomainNotFoundError(f"{label} not found")
        return read_model.model_validate(records[0]["node"])

    async def create_person(self, data: PersonCreate) -> PersonRead:
        """Create a person with an application-owned identifier."""
        return await self._create_node(
            label="Person",
            id_field="person_id",
            values=data.model_dump(mode="json"),
            read_model=PersonRead,
        )

    async def get_person(self, person_id: str) -> PersonRead:
        """Read one person by identifier."""
        return await self._get_node(
            label="Person",
            id_field="person_id",
            object_id=person_id,
            read_model=PersonRead,
        )

    async def list_persons(self) -> list[PersonRead]:
        """List people in display-name order."""
        records, _, _ = await self._driver.execute_query(
            """
            MATCH (person:Person)
            RETURN properties(person) AS node
            ORDER BY toLower(person.display_name), person.person_id
            """
        )
        return [PersonRead.model_validate(record["node"]) for record in records]

    async def bind_external_ref_person(
        self, person_id: str, external_ref_person_id: str
    ) -> PersonRead:
        """Bind one LifeGraph person to one explicit REF identity."""
        query = """
        MATCH (person:Person {person_id: $person_id})
        OPTIONAL MATCH (other:Person {external_ref_person_id: $external_ref_person_id})
        WITH person, other
        WHERE person.external_ref_person_id IS NULL
           OR person.external_ref_person_id = $external_ref_person_id
        WITH person, other
        WHERE other IS NULL OR other.person_id = person.person_id
        SET person.external_ref_person_id = $external_ref_person_id
        RETURN properties(person) AS node
        """
        try:
            records, _, _ = await self._driver.execute_query(
                query,
                person_id=person_id,
                external_ref_person_id=external_ref_person_id,
            )
        except ConstraintError as exc:
            raise DomainConflictError("REF person is already linked") from exc
        if records:
            return PersonRead.model_validate(records[0]["node"])
        try:
            person = await self.get_person(person_id)
        except DomainNotFoundError:
            raise
        if person.external_ref_person_id not in {None, external_ref_person_id}:
            raise DomainConflictError("LifeGraph person is linked to another REF person")
        raise DomainConflictError("REF person is already linked")

    async def create_conversation_turn(
        self, data: ConversationTurnCreate
    ) -> ConversationTurnRead:
        """Persist a conversation turn."""
        return await self._create_node(
            label="ConversationTurn",
            id_field="conversation_turn_id",
            values=data.model_dump(mode="json"),
            read_model=ConversationTurnRead,
        )

    async def get_conversation_turn(
        self, conversation_turn_id: str
    ) -> ConversationTurnRead:
        """Read one conversation turn."""
        return await self._get_node(
            label="ConversationTurn",
            id_field="conversation_turn_id",
            object_id=conversation_turn_id,
            read_model=ConversationTurnRead,
        )

    async def ensure_relation_review_turn(
        self,
        *,
        review_id: str,
        source_text: str,
    ) -> ConversationTurnRead:
        """Create or resolve the immutable USER turn backing one relation review."""

        turn_id = _new_id()
        properties = {
            "conversation_turn_id": turn_id,
            "created_at": _utc_now(),
            "text": source_text,
            "speaker": "USER",
            "review_extraction_id": review_id,
        }
        query = """
        MERGE (turn:ConversationTurn {review_extraction_id: $review_id})
          ON CREATE SET turn = $properties
        WITH turn
        WHERE turn.text = $source_text AND turn.speaker = 'USER'
        RETURN properties(turn) AS node
        """
        try:
            records, _, _ = await self._driver.execute_query(
                query,
                review_id=review_id,
                source_text=source_text,
                properties=properties,
            )
        except Neo4jError as exc:
            raise DomainPersistenceError("Graph persistence failed") from exc
        if not records:
            raise DomainConflictError("RELATION_REVIEW_TURN_CONFLICT")
        return ConversationTurnRead.model_validate(records[0]["node"])

    async def persist_relation_claim(
        self,
        claim: RelationClaim,
    ) -> tuple[RelationClaimGraphRead, bool]:
        """Atomically persist one reviewed declaration and all required edges."""

        properties = claim.model_dump(mode="json")
        creation_token = _new_id()
        query = """
        MATCH (endpoint_a:Person {person_id: $endpoint_a_person_id})
        MATCH (endpoint_b:Person {person_id: $endpoint_b_person_id})
        MATCH (turn:ConversationTurn {conversation_turn_id: $conversation_turn_id})
        WHERE endpoint_a.person_id <> endpoint_b.person_id
          AND turn.review_extraction_id = $review_id
          AND turn.text = $source_text
        MERGE (claim:RelationClaim {persistence_operation_key: $operation_key})
          ON CREATE SET claim = $properties, claim._creation_token = $creation_token
        WITH endpoint_a, endpoint_b, turn, claim
        WHERE claim.acceptance_payload_hash = $acceptance_payload_hash
          AND claim.review_id = $review_id
          AND claim.candidate_id = $candidate_id
        MERGE (claim)-[:ENDPOINT_A]->(endpoint_a)
        MERGE (claim)-[:ENDPOINT_B]->(endpoint_b)
        MERGE (claim)-[:EXTRACTED_FROM]->(turn)
        WITH endpoint_a, endpoint_b, turn, claim,
             claim._creation_token = $creation_token AS created
        REMOVE claim._creation_token
        RETURN properties(claim) AS claim,
               properties(endpoint_a) AS endpoint_a,
               properties(endpoint_b) AS endpoint_b,
               properties(turn) AS conversation_turn,
               created AS created
        """
        try:
            records, _, _ = await self._driver.execute_query(
                query,
                endpoint_a_person_id=claim.endpoint_a_person_id,
                endpoint_b_person_id=claim.endpoint_b_person_id,
                conversation_turn_id=claim.conversation_turn_id,
                review_id=claim.review_id,
                source_text=claim.source_text,
                operation_key=claim.persistence_operation_key,
                acceptance_payload_hash=claim.acceptance_payload_hash,
                candidate_id=claim.candidate_id,
                creation_token=creation_token,
                properties=properties,
            )
        except ConstraintError as exc:
            raise DomainConflictError("RELATION_CLAIM_PERSISTENCE_CONFLICT") from exc
        except Neo4jError as exc:
            logger.exception("Persistence error creating RelationClaim")
            raise DomainPersistenceError("Graph persistence failed") from exc
        if not records:
            raise DomainNotFoundError(
                "RelationClaim endpoint Person or source ConversationTurn not found"
            )
        row = records[0]
        graph = RelationClaimGraphRead(
            claim=RelationClaim.model_validate(row["claim"]),
            endpoint_a=PersonRead.model_validate(row["endpoint_a"]),
            endpoint_b=PersonRead.model_validate(row["endpoint_b"]),
            conversation_turn=ConversationTurnRead.model_validate(row["conversation_turn"]),
        )
        return graph, bool(row["created"])

    async def get_relation_claim_graph(
        self,
        relation_claim_id: str,
    ) -> RelationClaimGraphRead:
        """Read a RelationClaim with both endpoints and its source provenance."""

        query = """
        MATCH (claim:RelationClaim {relation_claim_id: $relation_claim_id})
              -[:ENDPOINT_A]->(endpoint_a:Person)
        MATCH (claim)-[:ENDPOINT_B]->(endpoint_b:Person)
        MATCH (claim)-[:EXTRACTED_FROM]->(turn:ConversationTurn)
        RETURN properties(claim) AS claim,
               properties(endpoint_a) AS endpoint_a,
               properties(endpoint_b) AS endpoint_b,
               properties(turn) AS conversation_turn
        """
        records, _, _ = await self._driver.execute_query(
            query, relation_claim_id=relation_claim_id
        )
        if not records:
            raise DomainNotFoundError("RelationClaim not found or incomplete")
        row = records[0]
        return RelationClaimGraphRead(
            claim=RelationClaim.model_validate(row["claim"]),
            endpoint_a=PersonRead.model_validate(row["endpoint_a"]),
            endpoint_b=PersonRead.model_validate(row["endpoint_b"]),
            conversation_turn=ConversationTurnRead.model_validate(row["conversation_turn"]),
        )

    async def create_claim_event(self, data: ClaimEventCreate) -> ClaimEventRead:
        """Persist a conversational claim event."""
        return await self._create_node(
            label="ClaimEvent",
            id_field="claim_event_id",
            values=data.model_dump(mode="json"),
            read_model=ClaimEventRead,
        )

    async def get_claim_event(self, claim_event_id: str) -> ClaimEventRead:
        """Read one claim event."""
        return await self._get_node(
            label="ClaimEvent",
            id_field="claim_event_id",
            object_id=claim_event_id,
            read_model=ClaimEventRead,
        )

    async def accept_extraction_candidate(
        self,
        *,
        person_id: str,
        source_text: str,
        extraction_id: str,
        candidate_id: str,
        pipeline_id: str,
        model_id: str,
        model_revision: str,
        candidate: ReviewCandidate,
        claim: ClaimEventCreate,
        correction_data: dict[str, Any],
        payload_hash: str,
        speaker: Any,
    ) -> dict[str, Any]:
        """Atomically persist an accepted candidate and its provenance."""
        accepted_key = f"{extraction_id}:{candidate_id}"
        claim_id = _new_id()
        turn_id = _new_id()
        created_at = _utc_now()
        claim_properties = {
            "claim_event_id": claim_id,
            "created_at": created_at,
            **claim.model_dump(mode="json"),
            "accepted_extraction_candidate_key": accepted_key,
            "extraction_id": extraction_id,
            "candidate_id": candidate_id,
            "pipeline_id": pipeline_id,
            "model_id": model_id,
            "model_revision": model_revision,
            "original_event_type": candidate.event_type.value,
            "original_trigger_text": candidate.trigger_text,
            "original_subject_text": candidate.subject_text,
            "original_subject_resolution": candidate.subject_resolution,
            "original_subject_reason": candidate.subject_reason,
            "original_participant_texts": candidate.participant_texts,
            "original_date_expression": candidate.date_expression,
            "original_model_score_metadata": candidate.model_score_metadata,
            "reviewer_correction_applied": bool(correction_data),
            "reviewer_corrections_json": json.dumps(correction_data, sort_keys=True),
            "acceptance_payload_hash": payload_hash,
        }
        turn_properties = {
            "conversation_turn_id": turn_id,
            "created_at": created_at,
            "text": source_text,
            "speaker": str(speaker),
            "review_extraction_id": extraction_id,
        }
        query = """
        MATCH (person:Person {person_id: $person_id})
        MERGE (claim:ClaimEvent {accepted_extraction_candidate_key: $accepted_key})
          ON CREATE SET claim = $claim_properties
        WITH person, claim
        WHERE claim.acceptance_payload_hash = $payload_hash
        MERGE (turn:ConversationTurn {review_extraction_id: $extraction_id})
          ON CREATE SET turn = $turn_properties
        MERGE (person)-[:SUBJECT_OF]->(claim)
        MERGE (claim)-[:EXTRACTED_FROM]->(turn)
        RETURN claim.claim_event_id AS claim_event_id,
               turn.conversation_turn_id AS conversation_turn_id,
               claim.acceptance_payload_hash AS stored_payload_hash,
               claim.claim_event_id = $new_claim_id AS created
        """
        try:
            records, _, _ = await self._driver.execute_query(
                query,
                person_id=person_id,
                extraction_id=extraction_id,
                accepted_key=accepted_key,
                claim_properties=claim_properties,
                turn_properties=turn_properties,
                new_claim_id=claim_id,
                payload_hash=payload_hash,
            )
        except Neo4jError as exc:
            logger.exception("Persistence error accepting extraction candidate")
            raise DomainPersistenceError("Graph persistence failed") from exc
        if not records:
            raise DomainConflictError("ACCEPTED_CANDIDATE_CONFLICT")
        row = records[0]
        if row["stored_payload_hash"] != payload_hash:
            raise DomainConflictError("ACCEPTED_CANDIDATE_CONFLICT")
        logger.info("Extraction candidate accepted extraction_id=%s candidate_id=%s", extraction_id, candidate_id)
        return {
            "extraction_id": extraction_id,
            "candidate_id": candidate_id,
            "person_id": person_id,
            "claim_event_id": row["claim_event_id"],
            "conversation_turn_id": row["conversation_turn_id"],
            "origin": "CONVERSATION",
            "verification_status": "DECLARED",
            "correction_applied": bool(correction_data),
            "created": bool(row["created"]),
        }

    async def create_ref_event(self, data: RefEventCreate) -> RefEventRead:
        """Persist a REF event."""
        return await self._create_node(
            label="RefEvent",
            id_field="ref_event_id",
            values=data.model_dump(mode="json"),
            read_model=RefEventRead,
        )

    async def upsert_imported_ref_event(
        self, data: RefEventCreate
    ) -> tuple[RefEventRead, bool]:
        """Create an imported REF event or return its existing node."""
        properties = {
            "ref_event_id": _new_id(),
            "created_at": _utc_now(),
            **data.model_dump(mode="json"),
        }
        query = """
        MERGE (event:RefEvent {external_ref_id: $external_ref_id})
        ON CREATE SET event = $properties
        ON MATCH SET event.event_date = $event_date,
                     event.registration_date = $registration_date
        RETURN properties(event) AS node,
               event.ref_event_id = $new_ref_event_id AS created
        """
        try:
            records, _, _ = await self._driver.execute_query(
                query,
                external_ref_id=data.external_ref_id,
                new_ref_event_id=properties["ref_event_id"],
                event_date=properties["event_date"],
                registration_date=properties["registration_date"],
                properties=properties,
            )
        except Neo4jError as exc:
            logger.exception("Persistence error importing RefEvent")
            raise DomainPersistenceError("Graph persistence failed") from exc
        record = records[0]
        node = RefEventRead.model_validate(record["node"])
        if node.origin != data.origin or node.event_type != data.event_type:
            raise DomainConflictError(
                "Existing RefEvent conflicts with the imported REF event"
            )
        return node, bool(record["created"])

    async def get_reconciliation_context(
        self, claim_event_id: str
    ) -> tuple[ClaimEventRead, list[RefEventRead]]:
        """Load a claim and same-person REF candidates of the same type."""
        query = """
        MATCH (claim:ClaimEvent {claim_event_id: $claim_event_id})
        OPTIONAL MATCH (person:Person)-[:SUBJECT_OF]->(claim)
        OPTIONAL MATCH (person)-[:PARTICIPATES_IN]->(candidate:RefEvent)
        WHERE candidate.event_type = claim.event_type
        RETURN properties(claim) AS claim,
               [item IN collect(DISTINCT candidate) WHERE item IS NOT NULL |
                properties(item)] AS candidates
        """
        try:
            records, _, _ = await self._driver.execute_query(
                query, claim_event_id=claim_event_id
            )
        except Neo4jError as exc:
            raise DomainPersistenceError("Graph persistence failed") from exc
        if not records:
            raise DomainNotFoundError("ClaimEvent not found")
        return (
            ClaimEventRead.model_validate(records[0]["claim"]),
            [RefEventRead.model_validate(item) for item in records[0]["candidates"]],
        )

    async def persist_reconciliation(
        self, claim_event_id: str, decision: ReconciliationDecision
    ) -> ReconciliationResult:
        """Persist a deterministic reconciliation decision idempotently."""
        reconciled_at = _utc_now()
        evidence_specs = []
        for reason in decision.reason_codes:
            ref_event_id = None
            if reason in {
                ReasonCode.EVENT_DATE_WITHIN_CLAIM_INTERVAL,
                ReasonCode.UNIQUE_TEMPORALLY_COMPATIBLE_CANDIDATE,
            }:
                ref_event_id = decision.matched_ref_event_id
            elif reason is ReasonCode.EVENT_DATE_OUTSIDE_CLAIM_INTERVAL:
                ref_event_id = next(iter(decision.contradictory_ref_event_ids), None)
            elif reason is ReasonCode.EVENT_TYPE_MATCH and len(
                decision.candidate_ref_event_ids
            ) == 1:
                ref_event_id = decision.candidate_ref_event_ids[0]
            discriminator = ref_event_id or "collective"
            evidence_specs.append(
                {
                    "evidence_key": f"reconciliation:{claim_event_id}:{reason.value}:{discriminator}",
                    "evidence_id": _new_id(),
                    "evidence_type": reason.value,
                    "description": REASON_DESCRIPTIONS[reason],
                    "source": RECONCILIATION_SOURCE,
                    "created_at": reconciled_at,
                    "ref_event_id": ref_event_id,
                }
            )

        async def write_reconciliation(tx):
            """Apply one reconciliation update inside a transaction."""
            claim_result = await tx.run(
                """
                MATCH (claim:ClaimEvent {claim_event_id: $claim_event_id})
                SET claim.verification_status = $status,
                    claim.reconciled_at = $reconciled_at,
                    claim.reconciliation_reason_codes = $reason_codes,
                    claim.reconciliation_candidate_ref_event_ids = $candidate_ids,
                    claim.matched_ref_event_id = $matched_ref_event_id
                RETURN claim.claim_event_id AS claim_event_id
                """,
                claim_event_id=claim_event_id,
                status=decision.status.value,
                reconciled_at=reconciled_at,
                reason_codes=[item.value for item in decision.reason_codes],
                candidate_ids=decision.candidate_ref_event_ids,
                matched_ref_event_id=decision.matched_ref_event_id,
            )
            if await claim_result.single() is None:
                raise DomainNotFoundError("ClaimEvent not found")

            await tx.run(
                """
                MATCH (claim:ClaimEvent {claim_event_id: $claim_event_id})
                      -[r:SUPPORTED_BY|CONTRADICTS]->()
                WHERE r.source = $source
                DELETE r
                """,
                claim_event_id=claim_event_id,
                source=RECONCILIATION_SOURCE,
            )
            if decision.matched_ref_event_id:
                await tx.run(
                    """
                    MATCH (claim:ClaimEvent {claim_event_id: $claim_event_id})
                    MATCH (event:RefEvent {ref_event_id: $ref_event_id})
                    MERGE (claim)-[r:SUPPORTED_BY]->(event)
                    SET r.source = $source
                    """,
                    claim_event_id=claim_event_id,
                    ref_event_id=decision.matched_ref_event_id,
                    source=RECONCILIATION_SOURCE,
                )
            for ref_event_id in decision.contradictory_ref_event_ids:
                await tx.run(
                    """
                    MATCH (claim:ClaimEvent {claim_event_id: $claim_event_id})
                    MATCH (event:RefEvent {ref_event_id: $ref_event_id})
                    MERGE (claim)-[r:CONTRADICTS]->(event)
                    SET r.source = $source
                    """,
                    claim_event_id=claim_event_id,
                    ref_event_id=ref_event_id,
                    source=RECONCILIATION_SOURCE,
                )

            desired_keys = [item["evidence_key"] for item in evidence_specs]
            await tx.run(
                """
                MATCH (e:Evidence {source: $source})-[:ABOUT]->
                      (claim:ClaimEvent {claim_event_id: $claim_event_id})
                WHERE NOT e.evidence_key IN $desired_keys
                DETACH DELETE e
                """,
                source=RECONCILIATION_SOURCE,
                claim_event_id=claim_event_id,
                desired_keys=desired_keys,
            )
            for spec in evidence_specs:
                await tx.run(
                    """
                    MATCH (claim:ClaimEvent {claim_event_id: $claim_event_id})
                    MERGE (e:Evidence {evidence_key: $spec.evidence_key})
                    ON CREATE SET e.evidence_id = $spec.evidence_id,
                                  e.evidence_type = $spec.evidence_type,
                                  e.description = $spec.description,
                                  e.source = $spec.source,
                                  e.created_at = $spec.created_at
                    MERGE (e)-[:ABOUT]->(claim)
                    WITH e
                    OPTIONAL MATCH (event:RefEvent {ref_event_id: $spec.ref_event_id})
                    FOREACH (_ IN CASE WHEN event IS NULL THEN [] ELSE [1] END |
                      MERGE (e)-[:DERIVED_FROM]->(event))
                    """,
                    claim_event_id=claim_event_id,
                    spec=spec,
                )

        try:
            async with self._driver.session() as session:
                await session.execute_write(write_reconciliation)
        except DomainNotFoundError:
            raise
        except Neo4jError as exc:
            logger.exception("Persistence error reconciling ClaimEvent")
            raise DomainPersistenceError("Graph persistence failed") from exc
        logger.info("ClaimEvent reconciled id=%s status=%s", claim_event_id, decision.status)
        return ReconciliationResult(
            claim_event_id=claim_event_id,
            status=decision.status,
            matched_ref_event_id=decision.matched_ref_event_id,
            candidate_ref_event_ids=decision.candidate_ref_event_ids,
            reason_codes=decision.reason_codes,
            reconciled_at=reconciled_at,
        )

    async def get_reconciliation_result(
        self, claim_event_id: str
    ) -> ReconciliationResult:
        """Read the current persisted reconciliation metadata."""
        claim = await self.get_claim_event(claim_event_id)
        records, _, _ = await self._driver.execute_query(
            """
            MATCH (claim:ClaimEvent {claim_event_id: $claim_event_id})
            RETURN claim.reconciled_at AS reconciled_at,
                   claim.matched_ref_event_id AS matched_ref_event_id,
                   claim.reconciliation_candidate_ref_event_ids AS candidate_ids,
                   claim.reconciliation_reason_codes AS reason_codes
            """,
            claim_event_id=claim_event_id,
        )
        row = records[0]
        if row["reconciled_at"] is None:
            raise DomainNotFoundError("ClaimEvent has not been reconciled")
        return ReconciliationResult(
            claim_event_id=claim_event_id,
            status=claim.verification_status,
            matched_ref_event_id=row["matched_ref_event_id"],
            candidate_ref_event_ids=row["candidate_ids"] or [],
            reason_codes=row["reason_codes"] or [],
            reconciled_at=row["reconciled_at"],
        )

    async def get_ref_event(self, ref_event_id: str) -> RefEventRead:
        """Read one REF event."""
        return await self._get_node(
            label="RefEvent",
            id_field="ref_event_id",
            object_id=ref_event_id,
            read_model=RefEventRead,
        )

    async def create_evidence(self, data: EvidenceCreate) -> EvidenceRead:
        """Persist an evidence node."""
        return await self._create_node(
            label="Evidence",
            id_field="evidence_id",
            values=data.model_dump(mode="json"),
            read_model=EvidenceRead,
        )

    async def get_evidence(self, evidence_id: str) -> EvidenceRead:
        """Read one evidence node."""
        return await self._get_node(
            label="Evidence",
            id_field="evidence_id",
            object_id=evidence_id,
            read_model=EvidenceRead,
        )

    async def _create_relationship(
        self,
        *,
        source_label: str,
        source_field: str,
        source_id: str,
        relationship: str,
        target_label: str,
        target_field: str,
        target_id: str,
        properties: dict[str, Any] | None = None,
    ) -> RelationshipRead:
        """Create an allow-listed relationship between existing nodes."""
        query = (
            f"MATCH (source:{source_label} {{{source_field}: $source_id}}) "
            f"MATCH (target:{target_label} {{{target_field}: $target_id}}) "
            f"MERGE (source)-[r:{relationship}]->(target) "
            "SET r += $properties "
            "RETURN properties(r) AS properties"
        )
        records, _, _ = await self._driver.execute_query(
            query,
            source_id=source_id,
            target_id=target_id,
            properties=properties or {},
        )
        if not records:
            raise DomainNotFoundError("Relationship endpoint not found")
        logger.info(
            "Relationship created type=%s source=%s target=%s",
            relationship,
            source_id,
            target_id,
        )
        return RelationshipRead(
            source=source_id,
            relationship=relationship,
            target=target_id,
            properties=records[0]["properties"],
        )

    async def link_person_claim(
        self, person_id: str, claim_event_id: str
    ) -> RelationshipRead:
        """Link a claim to its explicitly selected person."""
        return await self._create_relationship(
            source_label="Person",
            source_field="person_id",
            source_id=person_id,
            relationship="SUBJECT_OF",
            target_label="ClaimEvent",
            target_field="claim_event_id",
            target_id=claim_event_id,
        )

    async def link_claim_source(
        self, claim_event_id: str, conversation_turn_id: str
    ) -> RelationshipRead:
        """Link a claim to its source conversation turn."""
        return await self._create_relationship(
            source_label="ClaimEvent",
            source_field="claim_event_id",
            source_id=claim_event_id,
            relationship="EXTRACTED_FROM",
            target_label="ConversationTurn",
            target_field="conversation_turn_id",
            target_id=conversation_turn_id,
        )

    async def link_person_ref_event(
        self, person_id: str, ref_event_id: str, role: str
    ) -> RelationshipRead:
        """Link a person to a REF event with a registral role."""
        return await self._create_relationship(
            source_label="Person",
            source_field="person_id",
            source_id=person_id,
            relationship="PARTICIPATES_IN",
            target_label="RefEvent",
            target_field="ref_event_id",
            target_id=ref_event_id,
            properties={"role": role},
        )

    async def link_evidence_claim(
        self, evidence_id: str, claim_event_id: str
    ) -> RelationshipRead:
        """Link evidence to a claim."""
        return await self._create_relationship(
            source_label="Evidence",
            source_field="evidence_id",
            source_id=evidence_id,
            relationship="ABOUT",
            target_label="ClaimEvent",
            target_field="claim_event_id",
            target_id=claim_event_id,
        )

    async def link_evidence_ref_event(
        self, evidence_id: str, ref_event_id: str
    ) -> RelationshipRead:
        """Link evidence to a REF event."""
        return await self._create_relationship(
            source_label="Evidence",
            source_field="evidence_id",
            source_id=evidence_id,
            relationship="DERIVED_FROM",
            target_label="RefEvent",
            target_field="ref_event_id",
            target_id=ref_event_id,
        )

    async def link_claim_ref_event(
        self, claim_event_id: str, ref_event_id: str, relationship: str
    ) -> RelationshipRead:
        """Link a claim to supporting or contradicting REF evidence."""
        if relationship not in {"SUPPORTED_BY", "CONTRADICTS"}:
            raise ValueError("Unsupported explicit claim relationship")
        return await self._create_relationship(
            source_label="ClaimEvent",
            source_field="claim_event_id",
            source_id=claim_event_id,
            relationship=relationship,
            target_label="RefEvent",
            target_field="ref_event_id",
            target_id=ref_event_id,
        )

    async def get_graph(self) -> GraphRead:
        """Return supported nodes and relationships for visualization."""
        node_query = """
        MATCH (n)
        WHERE any(label IN labels(n) WHERE label IN $labels)
        RETURN labels(n)[0] AS type, properties(n) AS properties
        ORDER BY type, properties.created_at
        """
        edge_query = """
        MATCH (source)-[r]->(target)
        WHERE type(r) IN $relationships
        RETURN coalesce(
                 source.person_id, source.claim_event_id, source.ref_event_id,
                 source.relation_claim_id, source.conversation_turn_id, source.evidence_id
               ) AS source,
               coalesce(
                 target.person_id, target.claim_event_id, target.ref_event_id,
                 target.relation_claim_id, target.conversation_turn_id, target.evidence_id
               ) AS target,
               type(r) AS type,
               properties(r) AS properties
        ORDER BY type, source, target
        """
        labels = ["Person", "ClaimEvent", "RelationClaim", "RefEvent", "ConversationTurn", "Evidence"]
        relationships = [
            "SUBJECT_OF",
            "EXTRACTED_FROM",
            "PARTICIPATES_IN",
            "ABOUT",
            "DERIVED_FROM",
            "SUPPORTED_BY",
            "CONTRADICTS",
            "ENDPOINT_A",
            "ENDPOINT_B",
        ]
        node_records, _, _ = await self._driver.execute_query(
            node_query, labels=labels
        )
        edge_records, _, _ = await self._driver.execute_query(
            edge_query, relationships=relationships
        )
        id_fields = {
            "Person": "person_id",
            "ClaimEvent": "claim_event_id",
            "RelationClaim": "relation_claim_id",
            "RefEvent": "ref_event_id",
            "ConversationTurn": "conversation_turn_id",
            "Evidence": "evidence_id",
        }
        nodes = []
        for record in node_records:
            properties = dict(record["properties"])
            node_type = record["type"]
            nodes.append(
                GraphNode(
                    id=properties[id_fields[node_type]],
                    type=node_type,
                    properties=properties,
                )
            )
        edges = [
            GraphEdge(
                source=record["source"],
                target=record["target"],
                type=record["type"],
                properties=dict(record["properties"]),
            )
            for record in edge_records
        ]
        return GraphRead(nodes=nodes, edges=edges)
