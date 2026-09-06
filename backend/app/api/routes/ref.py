from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.ref.schemas import RefImportRequest, RefImportResult
from app.ref.service import RefImportService

router = APIRouter()


def get_import_service(request: Request) -> RefImportService:
    return request.app.state.ref_import_service


ImportService = Annotated[RefImportService, Depends(get_import_service)]


@router.post("/persons/{person_id}/ref/import", response_model=RefImportResult)
async def import_ref_trail(
    person_id: str, data: RefImportRequest, service: ImportService
) -> RefImportResult:
    return await service.import_person_trail(person_id, data.ref_person_id)
