"""FastAPI application for isolated GLiNER inference."""

import asyncio
from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI, HTTPException, Request, status

from app.model import GLiNERModel
from app.calibration import CONFIGURATIONS, extract_configuration
from app.schemas import ApprovedExtractionResult, AssociationRequest, CalibrationRequest, ExtractRequest
from app.subject_association import associate
from app.relation_extraction_b2 import extract_relations_b2
from app.relation_schemas import RelationExtractRequest, RelationExtractionResult

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")


def create_app(model_factory=GLiNERModel) -> FastAPI:
    """Build the extraction service and its managed model lifecycle."""
    @asynccontextmanager
    async def lifespan(application: FastAPI):
        """Load the model asynchronously and cancel pending work on shutdown."""
        model = model_factory()
        application.state.model = model
        load_task = asyncio.create_task(model.load())
        yield
        if not load_task.done():
            load_task.cancel()

    app = FastAPI(title="LifeGraph GLiNER Extraction Service", lifespan=lifespan)

    @app.get("/health")
    async def health() -> dict[str, str]:
        """Report that the HTTP process is running."""
        return {"status": "ok"}

    @app.get("/ready")
    async def ready(request: Request) -> dict[str, str]:
        """Report whether the model is loaded and ready for inference."""
        model = request.app.state.model
        if not model.ready:
            detail = "model_failed" if model.load_failed else "model_loading"
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=detail)
        return {"status": "ready", "model": "ok"}

    @app.post("/extract", response_model=ApprovedExtractionResult)
    async def extract(data: ExtractRequest, request: Request) -> ApprovedExtractionResult:
        """Run the immutable production extraction pipeline."""
        model = request.app.state.model
        if not model.ready:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="model unavailable",
            )
        try:
            return await model.extract(data.text)
        except RuntimeError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="model unavailable",
            ) from exc
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="inference failed",
            ) from exc

    @app.post("/relation-extract", response_model=RelationExtractionResult)
    async def relation_extract(data: RelationExtractRequest) -> RelationExtractionResult:
        """Run the frozen deterministic V1 relation extractor without GLiNER."""

        return extract_relations_b2(
            data.text,
            data.source_reference,
            "A0_B2",
        )

    @app.post("/calibration/extract")
    async def calibration_extract(data: CalibrationRequest, request: Request) -> dict:
        """Run one predefined calibration configuration."""
        model = request.app.state.model
        if not model.ready:
            raise HTTPException(status_code=503, detail="model unavailable")
        # Only immutable, predefined IDs reach the model; arbitrary schemas are impossible.
        config = CONFIGURATIONS[data.configuration_id]
        try:
            return await extract_configuration(model, config, data.text)
        except Exception as exc:
            raise HTTPException(status_code=500, detail="calibration inference failed") from exc

    @app.post("/calibration/associate")
    async def association(data: AssociationRequest, request: Request) -> dict:
        """Run one predefined subject-association strategy."""
        model = request.app.state.model
        if not model.ready:
            raise HTTPException(status_code=503, detail="model unavailable")
        try:
            return await associate(model, data.strategy_id, data.text)
        except Exception as exc:
            raise HTTPException(status_code=500, detail="association inference failed") from exc

    return app


app = create_app()
