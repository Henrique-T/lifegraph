from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from app.main import create_app


class StubGraphClient:
    def __init__(self, _settings) -> None:
        self.driver = None
        self.available = True

    async def initialize_schema(self) -> None:
        return None

    async def ping(self) -> bool:
        return self.available

    async def close(self) -> None:
        return None


def build_test_app():
    return create_app(StubGraphClient)


def test_health() -> None:
    app = build_test_app()
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_when_neo4j_is_available() -> None:
    app = build_test_app()
    with TestClient(app) as client:
        app.state.graph_client.ping = AsyncMock(return_value=True)
        response = client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready", "neo4j": "ok"}


def test_ready_when_neo4j_is_unavailable() -> None:
    app = build_test_app()
    with TestClient(app) as client:
        app.state.graph_client.ping = AsyncMock(return_value=False)
        response = client.get("/ready")
    assert response.status_code == 503
    assert response.json() == {"status": "not_ready", "neo4j": "unavailable"}
