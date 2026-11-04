"""FastAPI application factory and dependency lifecycle."""

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
from app.api.routes.relation_review import router as relation_review_router
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
from app.relation_review.client import RelationExtractionClient
from app.relation_review.service import RelationReviewService

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")


def create_app(
    graph_client_factory: Callable = Neo4jClient,
) -> FastAPI:
    """Build the LifeGraph API and configure managed service dependencies."""
    @asynccontextmanager
    async def lifespan(application: FastAPI):
        """Initialize and close application-scoped clients and services."""
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
        relation_extraction_client = RelationExtractionClient(settings)
        application.state.relation_extraction_client = relation_extraction_client
        application.state.relation_review_service = RelationReviewService(
            relation_extraction_client,
            application.state.graph_repository,
        )
        yield
        await relation_extraction_client.close()
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
        """Translate missing domain resources to HTTP 404."""
        return JSONResponse(
            {"detail": str(exception)}, status_code=status.HTTP_404_NOT_FOUND
        )

    @application.exception_handler(DomainConflictError)
    async def conflict_handler(
        _request: Request, exception: DomainConflictError
    ) -> JSONResponse:
        """Translate domain conflicts to HTTP 409."""
        return JSONResponse(
            {"detail": str(exception)}, status_code=status.HTTP_409_CONFLICT
        )

    @application.exception_handler(DomainPersistenceError)
    async def persistence_handler(
        _request: Request, _exception: DomainPersistenceError
    ) -> JSONResponse:
        """Hide persistence internals behind an HTTP 503 response."""
        return JSONResponse(
            {"detail": "Graph persistence unavailable"},
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    @application.exception_handler(RefPersonNotFoundError)
    async def ref_person_not_found_handler(
        _request: Request, _exception: RefPersonNotFoundError
    ) -> JSONResponse:
        """Translate missing REF identities to HTTP 404."""
        return JSONResponse(
            {"detail": "REF person not found"}, status_code=status.HTTP_404_NOT_FOUND
        )

    @application.exception_handler(RefNotConfiguredError)
    @application.exception_handler(RefUnavailableError)
    async def ref_unavailable_handler(
        _request: Request, exception: Exception
    ) -> JSONResponse:
        """Translate unavailable REF integration to HTTP 503."""
        return JSONResponse(
            {"detail": str(exception)},
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    @application.exception_handler(RefAuthenticationError)
    @application.exception_handler(RefMalformedResponseError)
    async def ref_bad_gateway_handler(
        _request: Request, exception: Exception
    ) -> JSONResponse:
        """Translate invalid REF responses or credentials to HTTP 502."""
        return JSONResponse(
            {"detail": str(exception)}, status_code=status.HTTP_502_BAD_GATEWAY
        )

    @application.exception_handler(ExtractionServiceUnavailableError)
    async def extraction_unavailable_handler(
        _request: Request, exception: ExtractionServiceUnavailableError
    ) -> JSONResponse:
        """Translate extraction-service unavailability to HTTP 503."""
        return JSONResponse(
            {"detail": str(exception)},
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    @application.exception_handler(MalformedExtractionResponseError)
    @application.exception_handler(ExtractionServiceError)
    async def extraction_gateway_handler(
        _request: Request, _exception: Exception
    ) -> JSONResponse:
        """Translate invalid extraction responses to HTTP 502."""
        return JSONResponse(
            {"detail": "GLiNER extraction failed"},
            status_code=status.HTTP_502_BAD_GATEWAY,
        )

    application.include_router(health_router)
    application.include_router(extraction_router)
    application.include_router(domain_router)
    application.include_router(ref_router)
    application.include_router(reconciliation_router)
    application.include_router(relation_review_router)
    return application


app = create_app()
