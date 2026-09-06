from uuid import UUID

from app.domain.enums import CivilEventType
from app.domain.schemas import RefEventCreate
from app.graph.repository import GraphRepository
from app.ref.client import RefClient
from app.ref.schemas import IgnoredRefEvent, RefImportResult, RefTrailEvent


def map_event_type(event: RefTrailEvent) -> CivilEventType | None:
    """Map only REF act types verified in the current canonical trail contract."""
    try:
        return CivilEventType(event.tipo)
    except ValueError:
        return None


class RefImportService:
    def __init__(self, client: RefClient, repository: GraphRepository) -> None:
        self._client = client
        self._repository = repository

    async def import_person_trail(
        self, person_id: str, ref_person_id: UUID
    ) -> RefImportResult:
        await self._repository.get_person(person_id)
        trail = await self._client.get_person_trail(ref_person_id)
        await self._repository.bind_external_ref_person(person_id, str(ref_person_id))

        created = 0
        existing = 0
        ignored: list[IgnoredRefEvent] = []
        for event in trail:
            event_type = map_event_type(event)
            if event_type is None:
                ignored.append(
                    IgnoredRefEvent(
                        id_ato=event.id_ato,
                        tipo=event.tipo,
                        papel=event.papel,
                        reason="unsupported_event_type",
                    )
                )
                continue
            ref_event, was_created = await self._repository.upsert_imported_ref_event(
                RefEventCreate(
                    external_ref_id=str(event.id_ato),
                    event_type=event_type,
                    event_date=event.data_evento,
                    registration_date=event.data_registro,
                )
            )
            await self._repository.link_person_ref_event(
                person_id, ref_event.ref_event_id, event.papel
            )
            if was_created:
                created += 1
            else:
                existing += 1

        return RefImportResult(
            person_id=person_id,
            ref_person_id=ref_person_id,
            retrieved_events=len(trail),
            created_events=created,
            existing_events=existing,
            ignored_events=ignored,
        )
