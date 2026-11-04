"""Live Neo4j integration test through the reconciliation HTTP boundary."""

import asyncio
from datetime import datetime, timezone
from uuid import uuid4

import httpx
import pytest
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.api.routes.reconciliation import router
from app.core.config import get_settings
from app.domain.schemas import ClaimEventCreate, PersonCreate, RefEventCreate
from app.graph.client import Neo4jClient
from app.graph.repository import DomainNotFoundError, GraphRepository
from app.reconciliation.engine import ReconciliationEngine

UTC = timezone.utc


@pytest.mark.integration
def test_reconciliation_post_and_get_use_real_repository() -> None:
    asyncio.run(_run())


async def _run() -> None:
    graph_client = Neo4jClient(get_settings())
    await graph_client.initialize_schema()
    repository = GraphRepository(graph_client.driver)
    app = FastAPI()
    app.state.reconciliation_engine = ReconciliationEngine(repository)

    @app.exception_handler(DomainNotFoundError)
    async def missing(_request: Request, exception: DomainNotFoundError) -> JSONResponse:
        return JSONResponse({"detail": str(exception)}, status_code=status.HTTP_404_NOT_FOUND)

    app.include_router(router)
    ids: list[str] = []
    claim_id = ""
    suffix = str(uuid4())
    try:
        person = await repository.create_person(PersonCreate(display_name=f"API reconciliation {suffix}"))
        ids.append(person.person_id)
        claim = await repository.create_claim_event(
            ClaimEventCreate(
                event_type="casamento",
                claimed_date_start=datetime(2019, 1, 1, tzinfo=UTC),
                claimed_date_end=datetime(2019, 12, 31, 23, 59, 59, tzinfo=UTC),
                temporal_precision="YEAR",
            )
        )
        claim_id = claim.claim_event_id
        ids.append(claim.claim_event_id)
        await repository.link_person_claim(person.person_id, claim.claim_event_id)
        ref_event = await repository.create_ref_event(
            RefEventCreate(
                external_ref_id=f"api-reconciliation-{suffix}",
                event_type="casamento",
                event_date=datetime(2019, 6, 15, tzinfo=UTC),
                registration_date=datetime(2019, 6, 16, tzinfo=UTC),
            )
        )
        ids.append(ref_event.ref_event_id)
        await repository.link_person_ref_event(person.person_id, ref_event.ref_event_id, "nubente")

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            post = await client.post(f"/claim-events/{claim.claim_event_id}/reconcile")
            get = await client.get(f"/claim-events/{claim.claim_event_id}/reconciliation")

        assert post.status_code == 200
        assert get.status_code == 200
        assert post.json()["status"] == get.json()["status"] == "CONFIRMED"
        assert post.json()["matched_ref_event_id"] == get.json()["matched_ref_event_id"] == ref_event.ref_event_id
        assert post.json()["claim_event_id"] == claim.claim_event_id
        assert "EVENT_DATE_WITHIN_CLAIM_INTERVAL" in post.json()["reason_codes"]
    finally:
        await graph_client.driver.execute_query(
            """
            MATCH (e:Evidence {source: 'RECONCILIATION_ENGINE'})-[:ABOUT]->
                  (claim:ClaimEvent {claim_event_id: $claim_id})
            DETACH DELETE e
            """,
            claim_id=claim_id,
        )
        await graph_client.driver.execute_query(
            """
            MATCH (n)
            WHERE coalesce(n.person_id, n.claim_event_id, n.ref_event_id, '') IN $ids
            DETACH DELETE n
            """,
            ids=ids,
        )
        await graph_client.close()
