"""API tests for health and readiness endpoints."""

from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from app.main import create_app


class StubGraphClient:
    """Minimal graph client used by application lifecycle tests."""

    def __init__(self, _settings) -> None:
        """Initialize an available in-memory client."""
        self.driver = None
        self.available = True

    async def initialize_schema(self) -> None:
        """Satisfy schema initialization without external I/O."""
        return None

    async def ping(self) -> bool:
        """Return the configured availability state."""
        return self.available

    async def close(self) -> None:
        """Satisfy the graph-client lifecycle interface."""
        return None


def build_test_app():
    """Exercise the build test app helper."""
    return create_app(StubGraphClient)


def test_health() -> None:
    """Verify health."""
    app = build_test_app()
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_when_neo4j_is_available() -> None:
    """Verify ready when neo4j is available."""
    app = build_test_app()
    with TestClient(app) as client:
        app.state.graph_client.ping = AsyncMock(return_value=True)
        response = client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready", "neo4j": "ok"}


def test_ready_when_neo4j_is_unavailable() -> None:
    """Verify ready when neo4j is unavailable."""
    app = build_test_app()
    with TestClient(app) as client:
        app.state.graph_client.ping = AsyncMock(return_value=False)
        response = client.get("/ready")
    assert response.status_code == 503
    assert response.json() == {"status": "not_ready", "neo4j": "unavailable"}
