from contextlib import asynccontextmanager
from collections.abc import Callable
import logging

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes.domain import router as domain_router
from app.api.routes.health import router as health_router
from app.api.routes.extraction import router as extraction_router
from app.api.routes.ref import router as ref_router
from app.api.routes.reconciliation import router as reconciliation_router
from app.core.config import get_settings
from app.graph.client import Neo4jClient
from app.graph.repository import (
    DomainConflictError,
    DomainNotFoundError,
    DomainPersistenceError,
    GraphRepository,
)
from app.extraction.client import (
    ExtractionClient,
    ExtractionServiceError,
    ExtractionServiceUnavailableError,
    MalformedExtractionResponseError,
)
from app.extraction.service import ExtractionService
from app.ref.client import (
    RefAuthenticationError,
    RefClient,
    RefMalformedResponseError,
    RefNotConfiguredError,
    RefPersonNotFoundError,
    RefUnavailableError,
)
from app.ref.service import RefImportService
from app.reconciliation.engine import ReconciliationEngine

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")


def create_app(
    graph_client_factory: Callable = Neo4jClient,
) -> FastAPI:
    @asynccontextmanager
    async def lifespan(application: FastAPI):
        settings = get_settings()
        graph_client = graph_client_factory(settings)
        await graph_client.initialize_schema()
        application.state.graph_client = graph_client
        application.state.graph_repository = GraphRepository(graph_client.driver)
        ref_client = RefClient(settings)
        application.state.ref_client = ref_client
        application.state.ref_import_service = RefImportService(
            ref_client, application.state.graph_repository
        )
        application.state.reconciliation_engine = ReconciliationEngine(
            application.state.graph_repository
        )
        extraction_client = ExtractionClient(settings)
        application.state.extraction_client = extraction_client
        application.state.extraction_service = ExtractionService(
            extraction_client, application.state.graph_repository
        )
        yield
        await extraction_client.close()
        await ref_client.close()
        await graph_client.close()

    application = FastAPI(
        title="LifeGraph Conversacional", version="0.2.0", lifespan=lifespan
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Accept", "Content-Type"],
    )

    @application.exception_handler(DomainNotFoundError)
    async def not_found_handler(
        _request: Request, exception: DomainNotFoundError
    ) -> JSONResponse:
        return JSONResponse(
            {"detail": str(exception)}, status_code=status.HTTP_404_NOT_FOUND
        )

    @application.exception_handler(DomainConflictError)
    async def conflict_handler(
        _request: Request, exception: DomainConflictError
    ) -> JSONResponse:
        return JSONResponse(
            {"detail": str(exception)}, status_code=status.HTTP_409_CONFLICT
        )

    @application.exception_handler(DomainPersistenceError)
    async def persistence_handler(
        _request: Request, _exception: DomainPersistenceError
    ) -> JSONResponse:
        return JSONResponse(
            {"detail": "Graph persistence unavailable"},
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    @application.exception_handler(RefPersonNotFoundError)
    async def ref_person_not_found_handler(
        _request: Request, _exception: RefPersonNotFoundError
    ) -> JSONResponse:
        return JSONResponse(
            {"detail": "REF person not found"}, status_code=status.HTTP_404_NOT_FOUND
        )

    @application.exception_handler(RefNotConfiguredError)
    @application.exception_handler(RefUnavailableError)
    async def ref_unavailable_handler(
        _request: Request, exception: Exception
    ) -> JSONResponse:
        return JSONResponse(
            {"detail": str(exception)},
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    @application.exception_handler(RefAuthenticationError)
    @application.exception_handler(RefMalformedResponseError)
    async def ref_bad_gateway_handler(
        _request: Request, exception: Exception
    ) -> JSONResponse:
        return JSONResponse(
            {"detail": str(exception)}, status_code=status.HTTP_502_BAD_GATEWAY
        )

    @application.exception_handler(ExtractionServiceUnavailableError)
    async def extraction_unavailable_handler(
        _request: Request, exception: ExtractionServiceUnavailableError
    ) -> JSONResponse:
        return JSONResponse(
            {"detail": str(exception)},
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    @application.exception_handler(MalformedExtractionResponseError)
    @application.exception_handler(ExtractionServiceError)
    async def extraction_gateway_handler(
        _request: Request, _exception: Exception
    ) -> JSONResponse:
        return JSONResponse(
            {"detail": "GLiNER extraction failed"},
            status_code=status.HTTP_502_BAD_GATEWAY,
        )

    application.include_router(health_router)
    application.include_router(extraction_router)
    application.include_router(domain_router)
    application.include_router(ref_router)
    application.include_router(reconciliation_router)
    return application


app = create_app()
