from uuid import UUID

import httpx
from pydantic import TypeAdapter, ValidationError

from app.core.config import Settings
from app.ref.schemas import RefTrailEvent


class RefIntegrationError(Exception):
    pass


class RefNotConfiguredError(RefIntegrationError):
    pass


class RefPersonNotFoundError(RefIntegrationError):
    pass


class RefAuthenticationError(RefIntegrationError):
    pass


class RefUnavailableError(RefIntegrationError):
    pass


class RefMalformedResponseError(RefIntegrationError):
    pass


class RefClient:
    """Narrow, read-only client for REF's canonical civil-trail endpoint."""

    def __init__(
        self,
        settings: Settings,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._token = settings.ref_bearer_token
        self._client = httpx.AsyncClient(
            base_url=str(settings.ref_base_url).rstrip("/"),
            timeout=httpx.Timeout(10.0),
            transport=transport,
        )

    async def get_person_trail(self, ref_person_id: UUID) -> list[RefTrailEvent]:
        if not self._token:
            raise RefNotConfiguredError("REF bearer token is not configured")
        try:
            response = await self._client.get(
                f"/pessoas/{ref_person_id}/trilha",
                headers={"Authorization": f"Bearer {self._token}"},
            )
        except httpx.RequestError as exc:
            raise RefUnavailableError("REF is unavailable") from exc

        if response.status_code == 404:
            raise RefPersonNotFoundError("REF person not found")
        if response.status_code in {401, 403}:
            raise RefAuthenticationError("REF rejected authentication")
        if response.status_code >= 400:
            raise RefUnavailableError(f"REF returned HTTP {response.status_code}")
        try:
            return TypeAdapter(list[RefTrailEvent]).validate_python(response.json())
        except (ValueError, ValidationError) as exc:
            raise RefMalformedResponseError("REF returned a malformed trail") from exc

    async def close(self) -> None:
        await self._client.aclose()
