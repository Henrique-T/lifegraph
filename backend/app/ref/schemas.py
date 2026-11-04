"""Validated schemas exchanged with the external REF service."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class RefTrailEvent(BaseModel):
    """Civil-trail event returned by REF."""
    model_config = ConfigDict(extra="ignore")

    id_ato: UUID
    tipo: str
    papel: str
    data_evento: datetime | None
    data_registro: datetime


class RefPersonSummary(BaseModel):
    """Minimal REF person record used for explicit selection."""
    model_config = ConfigDict(extra="ignore")

    id_pessoa: UUID
    cpn: str
    nome: str
    data_nascimento: date


class RefImportRequest(BaseModel):
    """Explicit request to import one known REF identity."""
    model_config = ConfigDict(extra="forbid")

    ref_person_id: UUID


class IgnoredRefEvent(BaseModel):
    """Unsupported REF event reported without persistence."""
    id_ato: UUID
    tipo: str
    papel: str
    reason: str


class RefImportResult(BaseModel):
    """Summary of an idempotent REF trail import."""
    person_id: str
    ref_person_id: UUID
    retrieved_events: int
    created_events: int
    existing_events: int
    ignored_events: list[IgnoredRefEvent]
