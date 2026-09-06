import httpx
from pydantic import ValidationError

from app.core.config import Settings
from app.extraction.schemas import PipelineExtractionResult


class ExtractionServiceError(Exception):
    pass


class ExtractionServiceUnavailableError(ExtractionServiceError):
    pass


class MalformedExtractionResponseError(ExtractionServiceError):
    pass


class ExtractionClient:
    def __init__(
        self,
        settings: Settings,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._client = httpx.AsyncClient(
            base_url=str(settings.gliner_base_url).rstrip("/"),
            timeout=httpx.Timeout(settings.gliner_timeout_seconds),
            transport=transport,
        )

    async def extract(self, text: str) -> PipelineExtractionResult:
        try:
            response = await self._client.post("/extract", json={"text": text})
        except httpx.RequestError as exc:
            raise ExtractionServiceUnavailableError(
                "GLiNER extraction service is unavailable"
            ) from exc
        if response.status_code == 503:
            raise ExtractionServiceUnavailableError(
                "GLiNER model is loading or unavailable"
            )
        if response.status_code >= 400:
            raise ExtractionServiceError(
                f"GLiNER extraction service returned HTTP {response.status_code}"
            )
        try:
            return PipelineExtractionResult.model_validate(response.json())
        except (ValueError, ValidationError) as exc:
            raise MalformedExtractionResponseError(
                "GLiNER extraction service returned malformed output"
            ) from exc

    async def close(self) -> None:
        await self._client.aclose()
