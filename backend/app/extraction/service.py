import asyncio
import hashlib
import json
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.domain.enums import Origin, Speaker, TemporalPrecision, VerificationStatus
from app.domain.schemas import ClaimEventCreate
from app.extraction.client import ExtractionClient
from app.extraction.schemas import (
    CandidateAcceptanceRequest,
    CandidateAcceptanceResult,
    CandidateRejectionResult,
    ExtractionRequest,
    ExtractionReview,
    ReviewCandidate,
    ReviewStatus,
)
from app.graph.repository import DomainConflictError, DomainNotFoundError, GraphRepository

REVIEW_TTL = timedelta(minutes=30)


class ExtractionService:
    """Owns ephemeral reviews; graph writes exist only in explicit accept()."""

    def __init__(self, client: ExtractionClient, repository: GraphRepository) -> None:
        self._client = client
        self._repository = repository
        self._reviews: dict[str, ExtractionReview] = {}
        self._acceptances: dict[tuple[str, str], tuple[str, CandidateAcceptanceResult]] = {}
        self._lock = asyncio.Lock()

    async def extract(self, request: ExtractionRequest) -> ExtractionReview:
        result = await self._client.extract(request.text)
        now = datetime.now(timezone.utc)
        review = ExtractionReview(
            extraction_id=str(uuid4()),
            source_text=result.source_text,
            model_id=result.model_id,
            model_revision=result.model_revision,
            pipeline_id=result.pipeline_id,
            candidates=[
                ReviewCandidate(candidate_id=str(uuid4()), **item.model_dump())
                for item in result.candidates
            ],
            warnings=result.warnings,
            latency_ms=result.latency_ms,
            expires_at=now + REVIEW_TTL,
        )
        async with self._lock:
            self._reviews[review.extraction_id] = review
        return review

    async def get_review(self, extraction_id: str) -> ExtractionReview:
        async with self._lock:
            review = self._reviews.get(extraction_id)
            if review is None or review.expires_at <= datetime.now(timezone.utc):
                self._reviews.pop(extraction_id, None)
                raise DomainNotFoundError("Extraction review not found or expired")
            return review.model_copy(deep=True)

    async def accept(
        self, extraction_id: str, candidate_id: str, request: CandidateAcceptanceRequest
    ) -> CandidateAcceptanceResult:
        review = await self.get_review(extraction_id)
        candidate = next((c for c in review.candidates if c.candidate_id == candidate_id), None)
        if candidate is None:
            raise DomainNotFoundError("Extraction candidate not found")
        if candidate.review_status is ReviewStatus.REJECTED:
            raise DomainConflictError("REJECTED_CANDIDATE_CONFLICT")

        corrections = request.corrections
        correction_data = corrections.model_dump(mode="json", exclude_unset=True)
        canonical = {"person_id": request.person_id, "corrections": correction_data}
        payload_hash = hashlib.sha256(
            json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        key = (extraction_id, candidate_id)
        async with self._lock:
            previous = self._acceptances.get(key)
            if previous:
                if previous[0] != payload_hash:
                    raise DomainConflictError("ACCEPTED_CANDIDATE_CONFLICT")
                return previous[1].model_copy(update={"created": False})

        # This explicit ID is the sole subject binding. No candidate text or
        # narrator marker is ever converted into a Person identity.
        await self._repository.get_person(request.person_id)
        normalized = candidate.normalized_time_candidate
        has_explicit_interval = {
            "claimed_date_start", "claimed_date_end", "temporal_precision"
        }.issubset(corrections.model_fields_set)
        if has_explicit_interval:
            date_start = corrections.claimed_date_start
            date_end = corrections.claimed_date_end
            precision = corrections.temporal_precision
        elif normalized is not None:
            date_start, date_end = normalized.start, normalized.end
            precision = TemporalPrecision(normalized.temporal_precision)
        else:
            date_start = date_end = None
            precision = TemporalPrecision.UNKNOWN
        claim = ClaimEventCreate(
            event_type=corrections.event_type or candidate.event_type,
            origin=Origin.CONVERSATION,
            verification_status=VerificationStatus.DECLARED,
            claimed_date_start=date_start,
            claimed_date_end=date_end,
            temporal_precision=precision or TemporalPrecision.UNKNOWN,
            temporal_uncertainty=corrections.temporal_uncertainty or False,
        )
        result = await self._repository.accept_extraction_candidate(
            person_id=request.person_id,
            source_text=review.source_text,
            extraction_id=extraction_id,
            candidate_id=candidate_id,
            pipeline_id=review.pipeline_id,
            model_id=review.model_id,
            model_revision=review.model_revision,
            candidate=candidate,
            claim=claim,
            correction_data=correction_data,
            payload_hash=payload_hash,
            speaker=Speaker.USER,
        )
        accepted = CandidateAcceptanceResult(**result)
        async with self._lock:
            current = self._reviews[extraction_id]
            for item in current.candidates:
                if item.candidate_id == candidate_id:
                    item.review_status = ReviewStatus.ACCEPTED
            self._acceptances[key] = (payload_hash, accepted)
        return accepted

    async def reject(self, extraction_id: str, candidate_id: str) -> CandidateRejectionResult:
        await self.get_review(extraction_id)
        key = (extraction_id, candidate_id)
        async with self._lock:
            review = self._reviews[extraction_id]
            candidate = next((c for c in review.candidates if c.candidate_id == candidate_id), None)
            if candidate is None:
                raise DomainNotFoundError("Extraction candidate not found")
            if key in self._acceptances or candidate.review_status is ReviewStatus.ACCEPTED:
                raise DomainConflictError("ACCEPTED_CANDIDATE_CONFLICT")
            candidate.review_status = ReviewStatus.REJECTED
        return CandidateRejectionResult(
            extraction_id=extraction_id,
            candidate_id=candidate_id,
            review_status="REJECTED",
        )
