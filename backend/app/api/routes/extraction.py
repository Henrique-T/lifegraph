from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status

from app.extraction.schemas import (
    CandidateAcceptanceRequest,
    CandidateAcceptanceResult,
    CandidateRejectionResult,
    ExtractionRequest,
    ExtractionReview,
)
from app.extraction.service import ExtractionService

router = APIRouter()


def get_service(request: Request) -> ExtractionService:
    return request.app.state.extraction_service


Service = Annotated[ExtractionService, Depends(get_service)]


@router.post("/extractions", response_model=ExtractionReview, status_code=status.HTTP_201_CREATED)
async def extract(data: ExtractionRequest, service: Service) -> ExtractionReview:
    return await service.extract(data)


@router.get("/extractions/{extraction_id}", response_model=ExtractionReview)
async def get_review(extraction_id: str, service: Service) -> ExtractionReview:
    return await service.get_review(extraction_id)


@router.post("/extractions/{extraction_id}/candidates/{candidate_id}/accept", response_model=CandidateAcceptanceResult)
async def accept_candidate(extraction_id: str, candidate_id: str, data: CandidateAcceptanceRequest, service: Service, response: Response) -> CandidateAcceptanceResult:
    result = await service.accept(extraction_id, candidate_id, data)
    response.status_code = status.HTTP_201_CREATED if result.created else status.HTTP_200_OK
    return result


@router.post("/extractions/{extraction_id}/candidates/{candidate_id}/reject", response_model=CandidateRejectionResult)
async def reject_candidate(extraction_id: str, candidate_id: str, service: Service) -> CandidateRejectionResult:
    return await service.reject(extraction_id, candidate_id)
