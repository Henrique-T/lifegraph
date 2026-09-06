import asyncio
from unittest.mock import AsyncMock

from app.extraction.schemas import ExtractionRequest, PipelineExtractionResult
from app.extraction.service import ExtractionService


def test_extraction_creates_review_but_does_not_write_graph() -> None:
    async def run() -> None:
        client = AsyncMock()
        client.extract.return_value = PipelineExtractionResult(
            source_text="Eu nasci em 1995.", model_id="model", model_revision="revision",
            pipeline_id="LIFEGRAPH_PT_CIVIL_V1", candidates=[], warnings=[], latency_ms=1,
        )
        repository = AsyncMock()
        service = ExtractionService(client, repository)
        review = await service.extract(ExtractionRequest(text="Eu nasci em 1995."))
        assert review.candidates == []
        client.extract.assert_awaited_once_with("Eu nasci em 1995.")
        repository.assert_not_called()

    asyncio.run(run())


def test_extraction_module_has_no_ref_dependency() -> None:
    from app.extraction import service

    names = set(service.__dict__)
    assert "RefClient" not in names
