"""Test api."""

import time

from fastapi.testclient import TestClient

from app.main import create_app
from app.schemas import ApprovedExtractionResult


class FakeModel:
    """Provide the FakeModel test double."""
    def __init__(self) -> None:
        """Initialize the test double."""
        self.ready = False
        self.load_failed = False

    async def load(self) -> None:
        """Simulate loading the extraction model."""
        self.ready = True

    async def extract(self, text: str):
        """Return deterministic extraction output for the test."""
        return ApprovedExtractionResult(source_text=text, model_id="fastino/gliner2.5-multi-v1", model_revision="aaecfe45db1d828c963717054ccb868e8ad1f1d5", pipeline_id="LIFEGRAPH_PT_CIVIL_V1", candidates=[], warnings=[], latency_ms=0.1)


class NeverReadyModel(FakeModel):
    """Provide the NeverReadyModel test double."""
    async def load(self) -> None:
        """Simulate loading the extraction model."""
        return None


def test_health_and_mocked_extraction() -> None:
    """Verify health and mocked extraction."""
    with TestClient(create_app(FakeModel)) as client:
        for _ in range(20):
            if client.get("/ready").status_code == 200:
                break
            time.sleep(0.01)
        response = client.post("/extract", json={"text": "texto"})
    assert response.status_code == 200
    assert response.json()["candidates"] == []
    assert response.json()["pipeline_id"] == "LIFEGRAPH_PT_CIVIL_V1"


def test_loading_model_returns_503() -> None:
    """Verify loading model returns 503."""
    with TestClient(create_app(NeverReadyModel)) as client:
        assert client.get("/health").status_code == 200
        response = client.post("/extract", json={"text": "texto"})
    assert response.status_code == 503
