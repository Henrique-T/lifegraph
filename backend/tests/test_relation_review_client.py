"""Frozen relation-extractor boundary tests."""

import json

import httpx
import pytest

from app.core.config import Settings
from app.extraction.client import (
    ExtractionServiceUnavailableError,
    MalformedExtractionResponseError,
)
from app.relation_review.client import RelationExtractionClient
from app.relation_review.service import CONFIGURATION_HASH


def payload() -> dict:
    return {
        "source_text": "João é pai de Maria.", "strategy": "A0", "threshold": 0.0,
        "detections": [],
        "candidates": [{
            "candidate_id": "c1", "source_reference": "r1", "source_text": "João é pai de Maria.",
            "relation_type": "FATHER_OF", "relation_surface_text": "pai de",
            "relation_span_start": 7, "relation_span_end": 13,
            "endpoint_a_mention": "João", "endpoint_a_span_start": 0, "endpoint_a_span_end": 4,
            "endpoint_a_resolution_state": "RESOLVED_MENTION",
            "endpoint_a_semantic_target": "EXPLICIT_MENTION",
            "endpoint_b_mention": "Maria", "endpoint_b_span_start": 14, "endpoint_b_span_end": 19,
            "endpoint_b_resolution_state": "RESOLVED_MENTION",
            "endpoint_b_semantic_target": "EXPLICIT_MENTION",
            "polarity": "POSITIVE", "epistemic_status": "ASSERTED", "reporting_mode": "DIRECT",
            "reporting_source_mention": None, "temporal_scope": "CURRENT_OR_UNSPECIFIED", "warnings": [],
            "pipeline_id": "LIFEGRAPH_PERSON_RELATION_V1", "model_id": "deterministic-structural-baseline",
            "model_revision": "A0_B2+B3+B4+COMPOUND_NAMES", "configuration_hash": CONFIGURATION_HASH,
            "detector_strategy": "A0", "detector_label": "deterministic-structural",
            "detector_confidence": 1.0, "persistence_eligibility": "NOT_PERSISTIBLE_UNBOUND_ENDPOINT",
        }],
    }


def client_for(handler) -> RelationExtractionClient:
    settings = Settings(neo4j_password="test")
    return RelationExtractionClient(settings, transport=httpx.MockTransport(handler))


@pytest.mark.anyio
async def test_client_validates_frozen_provenance_and_does_not_add_person_ids() -> None:
    seen = {}

    def handler(request: httpx.Request):
        seen.update(json.loads(request.content))
        return httpx.Response(200, json=payload())

    client = client_for(handler)
    candidates = await client.extract("João é pai de Maria.", "r1")
    await client.close()
    assert seen == {"text": "João é pai de Maria.", "source_reference": "r1"}
    assert candidates[0].configuration_hash == CONFIGURATION_HASH
    assert not any("person_id" in name for name in type(candidates[0]).model_fields)


@pytest.mark.anyio
async def test_client_rejects_changed_extraction_configuration() -> None:
    changed = payload()
    changed["candidates"][0]["configuration_hash"] = "changed"
    client = client_for(lambda _request: httpx.Response(200, json=changed))
    with pytest.raises(MalformedExtractionResponseError):
        await client.extract("text", "r1")
    await client.close()


@pytest.mark.anyio
async def test_client_maps_transport_failure() -> None:
    def handler(request: httpx.Request):
        raise httpx.ConnectError("offline", request=request)

    client = client_for(handler)
    with pytest.raises(ExtractionServiceUnavailableError):
        await client.extract("text", "r1")
    await client.close()
