"""Relation extraction and temporary review routes with no graph writes."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, status

from app.relation_review.schemas import (
    RelationAcceptanceRequest,
    RelationExtractionRequest,
    RelationRejectionRequest,
    RelationReviewActionResult,
    RelationReviewSession,
    RelationPersistenceRequest,
    RelationPersistenceResult,
)
from app.relation_review.service import RelationReviewService

router = APIRouter()


def get_service(request: Request) -> RelationReviewService:
    """Resolve the application-scoped temporary relation review service."""

    return request.app.state.relation_review_service


Service = Annotated[RelationReviewService, Depends(get_service)]


@router.post(
    "/relation-extractions",
    response_model=RelationReviewSession,
    status_code=status.HTTP_201_CREATED,
)
async def extract_relations(
    data: RelationExtractionRequest,
    service: Service,
) -> RelationReviewSession:
    """Run frozen extraction and create a temporary review session."""

    return await service.extract(data)


@router.get("/relation-reviews/{review_id}", response_model=RelationReviewSession)
async def get_relation_review(review_id: str, service: Service) -> RelationReviewSession:
    """Return one non-expired relation review session."""

    return await service.get_review(review_id)


@router.post(
    "/relation-reviews/{review_id}/candidates/{candidate_id}/accept",
    response_model=RelationReviewActionResult,
)
async def accept_relation_candidate(
    review_id: str,
    candidate_id: str,
    data: RelationAcceptanceRequest,
    service: Service,
) -> RelationReviewActionResult:
    """Approve a fully bound candidate for later persistence, without writing it."""

    return await service.accept(review_id, candidate_id, data)


@router.post(
    "/relation-reviews/{review_id}/candidates/{candidate_id}/reject",
    response_model=RelationReviewActionResult,
)
async def reject_relation_candidate(
    review_id: str,
    candidate_id: str,
    data: RelationRejectionRequest,
    service: Service,
) -> RelationReviewActionResult:
    """Terminally reject a candidate without graph mutation."""

    return await service.reject(review_id, candidate_id, data)


@router.post(
    "/relation-reviews/{review_id}/candidates/{candidate_id}/persist",
    response_model=RelationPersistenceResult,
)
async def persist_relation_candidate(
    review_id: str,
    candidate_id: str,
    _data: RelationPersistenceRequest,
    service: Service,
) -> RelationPersistenceResult:
    """Persist the already accepted server-side review without semantic input."""

    return await service.persist(review_id, candidate_id)
