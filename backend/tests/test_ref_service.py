"""Unit tests for explicit, idempotent REF trail import."""

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
    """Create an event fixture for the test."""
    return RefTrailEvent(
        id_ato=uuid4(),
        tipo=tipo,
        papel=papel,
        data_evento=None,
        data_registro=NOW,
    )


class FakeClient:
    """In-memory REF client used by import-service tests."""

    def __init__(self, trail: list[RefTrailEvent]) -> None:
        """Store the trail returned by the fake client."""
        self.trail = trail

    async def get_person_trail(self, ref_person_id: UUID) -> list[RefTrailEvent]:
        """Return the configured trail for the expected identity."""
        assert ref_person_id == REF_PERSON_ID
        return self.trail


class FakeRepository:
    """In-memory repository that records import operations."""

    def __init__(self) -> None:
        """Initialize recorded events, roles, and identity binding."""
        self.events: dict[str, RefEventRead] = {}
        self.roles: list[str] = []
        self.bound: str | None = None

    async def get_person(self, person_id: str) -> PersonRead:
        """Return the expected existing person."""
        assert person_id == PERSON_ID
        return PersonRead(person_id=person_id, display_name="Test", created_at=NOW)

    async def bind_external_ref_person(self, person_id: str, ref_id: str) -> PersonRead:
        """Record an explicit REF identity binding."""
        self.bound = ref_id
        return PersonRead(
            person_id=person_id,
            display_name="Test",
            created_at=NOW,
            external_ref_person_id=ref_id,
        )

    async def upsert_imported_ref_event(self, data):
        """Create a REF event once and report later calls as existing."""
        existing = data.external_ref_id in self.events
        if not existing:
            self.events[data.external_ref_id] = RefEventRead(
                **data.model_dump(), ref_event_id=str(uuid4()), created_at=NOW
            )
        return self.events[data.external_ref_id], not existing

    async def link_person_ref_event(self, _person_id: str, _event_id: str, role: str):
        """Record each distinct participation role."""
        if role not in self.roles:
            self.roles.append(role)


def test_current_ref_natimorto_is_a_direct_supported_type() -> None:
    """Verify current ref natimorto is a direct supported type."""
    assert map_event_type(event("natimorto", "natimorto")).value == "natimorto"


def test_unsupported_type_is_not_mapped() -> None:
    """Verify unsupported type is not mapped."""
    assert map_event_type(event("retificacao")) is None


def test_import_forces_ref_origin_preserves_role_and_is_idempotent() -> None:
    """Verify import forces ref origin preserves role and is idempotent."""
    asyncio.run(_test_import_forces_ref_origin_preserves_role_and_is_idempotent())


async def _test_import_forces_ref_origin_preserves_role_and_is_idempotent() -> None:
    """Run the asynchronous mport forces ref origin preserves role and is idempotent scenario."""
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
