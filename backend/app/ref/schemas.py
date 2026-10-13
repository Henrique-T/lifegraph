from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class RefTrailEvent(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id_ato: UUID
    tipo: str
    papel: str
    data_evento: datetime | None
    data_registro: datetime


class RefPersonSummary(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id_pessoa: UUID
    cpn: str
    nome: str
    data_nascimento: date


class RefImportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ref_person_id: UUID


class IgnoredRefEvent(BaseModel):
    id_ato: UUID
    tipo: str
    papel: str
    reason: str


class RefImportResult(BaseModel):
    person_id: str
    ref_person_id: UUID
    retrieved_events: int
    created_events: int
    existing_events: int
    ignored_events: list[IgnoredRefEvent]
