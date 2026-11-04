"""Infrastructure health and readiness routes."""

from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse

router = APIRouter(tags=["infrastructure"])


@router.get("/health")
async def health() -> dict[str, str]:
    """Report that the HTTP process is running."""
    return {"status": "ok"}


@router.get("/ready")
async def ready(request: Request) -> JSONResponse:
    """Report whether Neo4j is initialized and reachable."""
    if await request.app.state.graph_client.ping():
        return JSONResponse({"status": "ready", "neo4j": "ok"})
    return JSONResponse(
        {"status": "not_ready", "neo4j": "unavailable"},
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
    )
