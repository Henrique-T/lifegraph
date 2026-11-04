"""Routes for explicit, read-only REF access and trail import."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from app.ref.client import RefClient
from app.ref.schemas import RefImportRequest, RefImportResult, RefPersonSummary
from app.ref.service import RefImportService

router = APIRouter()


def get_import_service(request: Request) -> RefImportService:
    """Resolve the application-scoped REF import service."""
    return request.app.state.ref_import_service


def get_ref_client(request: Request) -> RefClient:
    """Resolve the application-scoped REF client."""
    return request.app.state.ref_client


ImportService = Annotated[RefImportService, Depends(get_import_service)]
RefClientDependency = Annotated[RefClient, Depends(get_ref_client)]


@router.get("/ref/persons", response_model=list[RefPersonSummary])
async def list_ref_people(
    client: RefClientDependency,
    limit: Annotated[int, Query(ge=1, le=50)] = 50,
) -> list[RefPersonSummary]:
    """List REF identities for an explicit user-selected LifeGraph binding."""
    return await client.list_people(limit)


@router.post("/persons/{person_id}/ref/import", response_model=RefImportResult)
async def import_ref_trail(
    person_id: str, data: RefImportRequest, service: ImportService
) -> RefImportResult:
    """Import one selected REF civil trail for a known LifeGraph person."""
    return await service.import_person_trail(person_id, data.ref_person_id)
