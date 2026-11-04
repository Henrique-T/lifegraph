"""Safety tests for process-local event extraction review state."""

import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError

from app.domain.schemas import PersonRead
from app.extraction.schemas import (
    CandidateAcceptanceRequest,
    ExtractionRequest,
    PipelineCandidate,
    PipelineExtractionResult,
)
from app.extraction.service import ExtractionService
from app.graph.repository import DomainNotFoundError


def _service() -> tuple[ExtractionService, AsyncMock]:
    client = AsyncMock()
    repository = AsyncMock()
    client.extract.return_value = PipelineExtractionResult(
        source_text="Eu nasci em 1990.",
        model_id="fastino/gliner2.5-multi-v1",
        model_revision="aaecfe45db1d828c963717054ccb868e8ad1f1d5",
        pipeline_id="LIFEGRAPH_PT_CIVIL_V1",
        warnings=[],
        latency_ms=1,
        candidates=[
            PipelineCandidate(
                event_type="nascimento",
                trigger_text="nasci",
                trigger_start=3,
                trigger_end=8,
                subject_text="__NARRATOR__",
                subject_resolution="RESOLVED",
                subject_reason="EXPLICIT_FIRST_PERSON_PRONOUN",
                participant_texts=[],
                date_expression="1990",
                normalized_time_candidate={
                    "start": "1990-01-01T00:00:00Z",
                    "end": "1990-12-31T23:59:59.999999Z",
                    "temporal_precision": "YEAR",
                    "normalization_method": "DETERMINISTIC_YEAR_PATTERN",
                },
                warnings=[],
            )
        ],
    )
    repository.get_person.return_value = PersonRead(
        person_id="person-1",
        display_name="Pessoa",
        created_at="2026-01-01T00:00:00Z",
    )
    return ExtractionService(client, repository), repository


def _assert_no_acceptance_write(repository: AsyncMock) -> None:
    repository.get_person.assert_not_awaited()
    repository.accept_extraction_candidate.assert_not_awaited()


def test_pending_review_is_available_before_expiration() -> None:
    async def run() -> None:
        service, repository = _service()
        created = await service.extract(ExtractionRequest(text="Eu nasci em 1990."))
        fetched = await service.get_review(created.extraction_id)
        assert fetched.extraction_id == created.extraction_id
        assert fetched.candidates[0].candidate_id == created.candidates[0].candidate_id
        _assert_no_acceptance_write(repository)

    asyncio.run(run())


def test_expired_review_cannot_be_accepted_and_leaves_no_acceptance_artifact() -> None:
    async def run() -> None:
        service, repository = _service()
        review = await service.extract(ExtractionRequest(text="Eu nasci em 1990."))
        service._reviews[review.extraction_id].expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)

        with pytest.raises(DomainNotFoundError, match="not found or expired"):
            await service.accept(
                review.extraction_id,
                review.candidates[0].candidate_id,
                CandidateAcceptanceRequest(person_id="person-1"),
            )

        assert review.extraction_id not in service._reviews
        assert service._acceptances == {}
        _assert_no_acceptance_write(repository)

    asyncio.run(run())


def test_unknown_review_cannot_be_accepted() -> None:
    async def run() -> None:
        service, repository = _service()
        with pytest.raises(DomainNotFoundError, match="not found or expired"):
            await service.accept(
                "missing-review",
                "missing-candidate",
                CandidateAcceptanceRequest(person_id="person-1"),
            )
        _assert_no_acceptance_write(repository)

    asyncio.run(run())


def test_lost_process_local_review_cannot_be_reconstructed_for_acceptance() -> None:
    async def run() -> None:
        service, repository = _service()
        review = await service.extract(ExtractionRequest(text="Eu nasci em 1990."))
        candidate_id = review.candidates[0].candidate_id
        service._reviews.clear()  # semantic equivalent of a backend restart

        with pytest.raises(DomainNotFoundError, match="not found or expired"):
            await service.accept(
                review.extraction_id,
                candidate_id,
                CandidateAcceptanceRequest(person_id="person-1"),
            )
        assert service._acceptances == {}
        _assert_no_acceptance_write(repository)

    asyncio.run(run())


@pytest.mark.parametrize(
    "override",
    [
        {"source_text": "Eu nasci em 1990."},
        {"candidate_id": "client-candidate"},
        {"origin": "CONVERSATION"},
        {"verification_status": "DECLARED"},
        {"pipeline_id": "client-pipeline"},
    ],
)
def test_acceptance_request_cannot_reconstruct_missing_server_review(override: dict[str, str]) -> None:
    with pytest.raises(ValidationError):
        CandidateAcceptanceRequest.model_validate({"person_id": "person-1", **override})
