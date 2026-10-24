import logging

from neo4j import AsyncDriver, AsyncGraphDatabase
from neo4j.exceptions import Neo4jError

from app.core.config import Settings

logger = logging.getLogger(__name__)

SCHEMA_STATEMENTS = (
    "CREATE CONSTRAINT person_id_unique IF NOT EXISTS "
    "FOR (n:Person) REQUIRE n.person_id IS UNIQUE",
    "CREATE CONSTRAINT person_external_ref_id_unique IF NOT EXISTS "
    "FOR (n:Person) REQUIRE n.external_ref_person_id IS UNIQUE",
    "CREATE CONSTRAINT claim_event_id_unique IF NOT EXISTS "
    "FOR (n:ClaimEvent) REQUIRE n.claim_event_id IS UNIQUE",
    "CREATE CONSTRAINT ref_event_id_unique IF NOT EXISTS "
    "FOR (n:RefEvent) REQUIRE n.ref_event_id IS UNIQUE",
    "CREATE CONSTRAINT ref_event_external_id_unique IF NOT EXISTS "
    "FOR (n:RefEvent) REQUIRE n.external_ref_id IS UNIQUE",
    "CREATE CONSTRAINT conversation_turn_id_unique IF NOT EXISTS "
    "FOR (n:ConversationTurn) REQUIRE n.conversation_turn_id IS UNIQUE",
    "CREATE CONSTRAINT evidence_id_unique IF NOT EXISTS "
    "FOR (n:Evidence) REQUIRE n.evidence_id IS UNIQUE",
    "CREATE CONSTRAINT evidence_key_unique IF NOT EXISTS "
    "FOR (n:Evidence) REQUIRE n.evidence_key IS UNIQUE",
    "CREATE CONSTRAINT accepted_candidate_key_unique IF NOT EXISTS "
    "FOR (n:ClaimEvent) REQUIRE n.accepted_extraction_candidate_key IS UNIQUE",
    "CREATE CONSTRAINT review_extraction_turn_unique IF NOT EXISTS "
    "FOR (n:ConversationTurn) REQUIRE n.review_extraction_id IS UNIQUE",
    "CREATE CONSTRAINT relation_claim_id_unique IF NOT EXISTS "
    "FOR (n:RelationClaim) REQUIRE n.relation_claim_id IS UNIQUE",
    "CREATE CONSTRAINT relation_claim_operation_unique IF NOT EXISTS "
    "FOR (n:RelationClaim) REQUIRE n.persistence_operation_key IS UNIQUE",
    "CREATE INDEX claim_event_type_index IF NOT EXISTS "
    "FOR (n:ClaimEvent) ON (n.event_type)",
    "CREATE INDEX claim_verification_status_index IF NOT EXISTS "
    "FOR (n:ClaimEvent) ON (n.verification_status)",
    "CREATE INDEX relation_claim_type_index IF NOT EXISTS "
    "FOR (n:RelationClaim) ON (n.relation_type)",
    "CREATE INDEX ref_event_type_index IF NOT EXISTS "
    "FOR (n:RefEvent) ON (n.event_type)",
)


class Neo4jClient:
    def __init__(self, settings: Settings) -> None:
        self._driver: AsyncDriver = AsyncGraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )
        self.schema_initialized = False

    @property
    def driver(self) -> AsyncDriver:
        return self._driver

    async def initialize_schema(self) -> None:
        async with self._driver.session() as session:
            for statement in SCHEMA_STATEMENTS:
                await session.run(statement)
        self.schema_initialized = True
        logger.info("Neo4j domain schema initialized")

    async def ping(self) -> bool:
        if not self.schema_initialized:
            return False
        try:
            async with self._driver.session() as session:
                result = await session.run("RETURN 1 AS value")
                record = await result.single(strict=True)
                return record["value"] == 1
        except (Neo4jError, OSError):
            return False

    async def close(self) -> None:
        await self._driver.close()
