"""C1 boundary tests for the frozen deterministic relation extractor."""

from fastapi.testclient import TestClient

from app.main import create_app


class NeverLoadedModel:
    ready = False
    load_failed = False

    async def load(self) -> None:
        return None


def test_relation_endpoint_uses_frozen_deterministic_pipeline_without_gliner() -> None:
    with TestClient(create_app(NeverLoadedModel)) as client:
        response = client.post(
            "/relation-extract",
            json={"text": "João é pai de Maria.", "source_reference": "review-1"},
        )
    assert response.status_code == 200
    payload = response.json()
    assert payload["strategy"] == "A0"
    assert len(payload["candidates"]) == 1
    relation = payload["candidates"][0]
    assert relation["pipeline_id"] == "LIFEGRAPH_PERSON_RELATION_V1"
    assert relation["model_revision"] == "A0_B2+B3+B4"
    assert relation["configuration_hash"] == "32040A53D33F30A4DDDBA0E423180AB9DC08AF17B583BB6B3A9A82BEA091FC7D"
    assert "endpoint_a_person_id" not in relation


def test_relation_endpoint_is_strict_and_does_not_change_event_extract_readiness() -> None:
    with TestClient(create_app(NeverLoadedModel)) as client:
        relation = client.post(
            "/relation-extract",
            json={"text": "João é pai de Maria.", "source_reference": "r", "origin": "CONVERSATION"},
        )
        event = client.post("/extract", json={"text": "João nasceu."})
    assert relation.status_code == 422
    assert event.status_code == 503
