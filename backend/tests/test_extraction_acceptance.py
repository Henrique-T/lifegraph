"""Unit tests for explicit extraction acceptance and rejection."""

import asyncio
from unittest.mock import AsyncMock

import pytest

from app.domain.schemas import PersonRead
from app.extraction.schemas import (
    CandidateAcceptanceRequest,
    CandidateCorrections,
    ExtractionRequest,
    PipelineCandidate,
    PipelineExtractionResult,
)
from app.extraction.service import ExtractionService
from app.graph.repository import DomainConflictError, DomainNotFoundError


def pipeline(subject="__NARRATOR__", resolution="RESOLVED"):
    """Create a pipeline fixture for the test."""
    return PipelineExtractionResult(
        source_text="Eu me casei com Ana em 2019.", model_id="fastino/gliner2.5-multi-v1",
        model_revision="aaecfe45db1d828c963717054ccb868e8ad1f1d5",
        pipeline_id="LIFEGRAPH_PT_CIVIL_V1", warnings=[], latency_ms=1,
        candidates=[PipelineCandidate(
            event_type="casamento", trigger_text="me casei", trigger_start=3, trigger_end=11,
            subject_text=subject, subject_resolution=resolution,
            subject_reason="EXPLICIT_FIRST_PERSON_PRONOUN" if subject else "NO_SAFE_SUBJECT_EVIDENCE",
            participant_texts=["Ana"], date_expression="2019",
            normalized_time_candidate={"start":"2019-01-01T00:00:00Z", "end":"2019-12-31T23:59:59.999999Z", "temporal_precision":"YEAR", "normalization_method":"DETERMINISTIC_YEAR_PATTERN"},
            warnings=[]
        )]
    )


def make_service(result=None):
    """Exercise the make service helper."""
    client, repository = AsyncMock(), AsyncMock()
    client.extract.return_value = result or pipeline()
    repository.get_person.return_value = PersonRead(person_id="person-1", display_name="Ana", created_at="2026-01-01T00:00:00Z")
    repository.accept_extraction_candidate.return_value = {
        "extraction_id":"", "candidate_id":"", "person_id":"person-1",
        "claim_event_id":"claim-1", "conversation_turn_id":"turn-1",
        "origin":"CONVERSATION", "verification_status":"DECLARED",
        "correction_applied":False, "created":True,
    }
    return ExtractionService(client, repository), repository


def test_accept_is_explicit_declared_conversation_and_idempotent():
    """Verify accept is explicit declared conversation and idempotent."""
    async def run():
        """Run the asynchronous test scenario."""
        service, repo = make_service()
        review = await service.extract(ExtractionRequest(text="Eu me casei com Ana em 2019."))
        candidate = review.candidates[0]
        repo.accept_extraction_candidate.return_value.update(extraction_id=review.extraction_id, candidate_id=candidate.candidate_id)
        request = CandidateAcceptanceRequest(person_id="person-1")
        first = await service.accept(review.extraction_id, candidate.candidate_id, request)
        second = await service.accept(review.extraction_id, candidate.candidate_id, request)
        assert (first.origin, first.verification_status, first.created) == ("CONVERSATION", "DECLARED", True)
        assert second.created is False
        repo.accept_extraction_candidate.assert_awaited_once()
    asyncio.run(run())


def test_conflicting_reaccept_is_rejected():
    """Verify conflicting reaccept is rejected."""
    async def run():
        """Run the asynchronous test scenario."""
        service, repo = make_service()
        review = await service.extract(ExtractionRequest(text="x")); candidate = review.candidates[0]
        repo.accept_extraction_candidate.return_value.update(extraction_id=review.extraction_id, candidate_id=candidate.candidate_id)
        await service.accept(review.extraction_id, candidate.candidate_id, CandidateAcceptanceRequest(person_id="person-1"))
        with pytest.raises(DomainConflictError, match="ACCEPTED_CANDIDATE_CONFLICT"):
            await service.accept(review.extraction_id, candidate.candidate_id, CandidateAcceptanceRequest(person_id="person-2"))
    asyncio.run(run())


def test_reject_is_graph_noop_and_unknown_person_blocks_acceptance():
    """Verify reject is graph noop and unknown person blocks acceptance."""
    async def run():
        """Run the asynchronous test scenario."""
        service, repo = make_service(pipeline(None, "UNRESOLVED"))
        review = await service.extract(ExtractionRequest(text="x")); candidate = review.candidates[0]
        rejected = await service.reject(review.extraction_id, candidate.candidate_id)
        assert (rejected.graph_delta_nodes, rejected.graph_delta_edges) == (0, 0)
        repo.accept_extraction_candidate.assert_not_awaited()

        service2, repo2 = make_service(pipeline("Meu irmão"))
        repo2.get_person.side_effect = DomainNotFoundError("Person not found")
        review2 = await service2.extract(ExtractionRequest(text="x")); candidate2 = review2.candidates[0]
        with pytest.raises(DomainNotFoundError):
            await service2.accept(review2.extraction_id, candidate2.candidate_id, CandidateAcceptanceRequest(person_id="missing"))
        repo2.accept_extraction_candidate.assert_not_awaited()
    asyncio.run(run())


def test_corrections_are_explicit_and_origin_status_are_forbidden():
    """Verify corrections are explicit and origin status are forbidden."""
    with pytest.raises(Exception):
        CandidateAcceptanceRequest.model_validate({"person_id":"p", "origin":"REF"})
    with pytest.raises(Exception):
        CandidateAcceptanceRequest.model_validate({"person_id":"p", "verification_status":"CONFIRMED"})
    corrected = CandidateCorrections(subject_text="Meu irmão", event_type="nascimento")
    assert corrected.model_dump(exclude_unset=True) == {"subject_text":"Meu irmão", "event_type":"nascimento"}
