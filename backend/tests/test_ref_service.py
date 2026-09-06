import asyncio
from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.domain.enums import Origin
from app.domain.schemas import PersonRead, RefEventRead
from app.ref.schemas import RefTrailEvent
from app.ref.service import RefImportService, map_event_type

PERSON_ID = "lifegraph-person"
REF_PERSON_ID = UUID("73bacb7c-2806-457a-b910-62d93a4b9959")
NOW = datetime.now(timezone.utc)


def event(tipo: str, papel: str = "registrando") -> RefTrailEvent:
    return RefTrailEvent(
        id_ato=uuid4(),
        tipo=tipo,
        papel=papel,
        data_evento=None,
        data_registro=NOW,
    )


class FakeClient:
    def __init__(self, trail: list[RefTrailEvent]) -> None:
        self.trail = trail

    async def get_person_trail(self, ref_person_id: UUID) -> list[RefTrailEvent]:
        assert ref_person_id == REF_PERSON_ID
        return self.trail


class FakeRepository:
    def __init__(self) -> None:
        self.events: dict[str, RefEventRead] = {}
        self.roles: list[str] = []
        self.bound: str | None = None

    async def get_person(self, person_id: str) -> PersonRead:
        assert person_id == PERSON_ID
        return PersonRead(person_id=person_id, display_name="Test", created_at=NOW)

    async def bind_external_ref_person(self, person_id: str, ref_id: str) -> PersonRead:
        self.bound = ref_id
        return PersonRead(
            person_id=person_id,
            display_name="Test",
            created_at=NOW,
            external_ref_person_id=ref_id,
        )

    async def upsert_imported_ref_event(self, data):
        existing = data.external_ref_id in self.events
        if not existing:
            self.events[data.external_ref_id] = RefEventRead(
                **data.model_dump(), ref_event_id=str(uuid4()), created_at=NOW
            )
        return self.events[data.external_ref_id], not existing

    async def link_person_ref_event(self, _person_id: str, _event_id: str, role: str):
        if role not in self.roles:
            self.roles.append(role)


def test_current_ref_natimorto_is_a_direct_supported_type() -> None:
    assert map_event_type(event("natimorto", "natimorto")).value == "natimorto"


def test_unsupported_type_is_not_mapped() -> None:
    assert map_event_type(event("retificacao")) is None


def test_import_forces_ref_origin_preserves_role_and_is_idempotent() -> None:
    asyncio.run(_test_import_forces_ref_origin_preserves_role_and_is_idempotent())


async def _test_import_forces_ref_origin_preserves_role_and_is_idempotent() -> None:
    trail = [event("nascimento"), event("unsupported", "secondary")]
    repository = FakeRepository()
    service = RefImportService(FakeClient(trail), repository)

    first = await service.import_person_trail(PERSON_ID, REF_PERSON_ID)
    second = await service.import_person_trail(PERSON_ID, REF_PERSON_ID)

    assert first.created_events == 1
    assert first.existing_events == 0
    assert first.ignored_events[0].reason == "unsupported_event_type"
    assert second.created_events == 0
    assert second.existing_events == 1
    assert repository.roles == ["registrando"]
    assert repository.bound == str(REF_PERSON_ID)
    assert next(iter(repository.events.values())).origin is Origin.REF
