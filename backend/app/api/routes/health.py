from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse

router = APIRouter(tags=["infrastructure"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready")
async def ready(request: Request) -> JSONResponse:
    if await request.app.state.graph_client.ping():
        return JSONResponse({"status": "ready", "neo4j": "ok"})
    return JSONResponse(
        {"status": "not_ready", "neo4j": "unavailable"},
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
    )
