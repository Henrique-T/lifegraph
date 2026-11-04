"""Read-only HTTP integration with the external REF service."""

from uuid import UUID

import httpx
from pydantic import TypeAdapter, ValidationError

from app.core.config import Settings
from app.ref.schemas import RefPersonSummary, RefTrailEvent


class RefIntegrationError(Exception):
    """Base error raised by the REF integration boundary."""


class RefNotConfiguredError(RefIntegrationError):
    """Raised when REF authentication is not configured."""


class RefPersonNotFoundError(RefIntegrationError):
    """Raised when REF does not contain the requested person."""


class RefAuthenticationError(RefIntegrationError):
    """Raised when REF rejects the configured credentials."""


class RefUnavailableError(RefIntegrationError):
    """Raised when REF cannot serve a request."""


class RefMalformedResponseError(RefIntegrationError):
    """Raised when REF output violates the expected schema."""


class RefClient:
    """Narrow, read-only client for REF's canonical civil-trail endpoint."""

    def __init__(
        self,
        settings: Settings,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        """Configure the authenticated, read-only REF client."""
        self._token = settings.ref_bearer_token
        self._client = httpx.AsyncClient(
            base_url=str(settings.ref_base_url).rstrip("/"),
            timeout=httpx.Timeout(10.0),
            transport=transport,
        )

    def _authorization_headers(self) -> dict[str, str]:
        """Build the required bearer authorization header."""
        if not self._token:
            raise RefNotConfiguredError("REF bearer token is not configured")
        return {"Authorization": f"Bearer {self._token}"}

    async def list_people(self, limit: int = 50) -> list[RefPersonSummary]:
        """List the most recently available REF people up to the limit."""
        try:
            response = await self._client.get(
                "/pessoas/recent",
                params={"limit": limit},
                headers=self._authorization_headers(),
            )
        except httpx.RequestError as exc:
            raise RefUnavailableError("REF is unavailable") from exc

        if response.status_code in {401, 403}:
            raise RefAuthenticationError("REF rejected authentication")
        if response.status_code >= 400:
            raise RefUnavailableError(f"REF returned HTTP {response.status_code}")
        try:
            return TypeAdapter(list[RefPersonSummary]).validate_python(response.json())
        except (ValueError, ValidationError) as exc:
            raise RefMalformedResponseError("REF returned a malformed person list") from exc

    async def get_person_trail(self, ref_person_id: UUID) -> list[RefTrailEvent]:
        """Retrieve the canonical civil trail for one REF identity."""
        try:
            response = await self._client.get(
                f"/pessoas/{ref_person_id}/trilha",
                headers=self._authorization_headers(),
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
        """Release HTTP resources."""
        await self._client.aclose()
