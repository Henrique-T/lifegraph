import asyncio

import httpx
import pytest

from app.core.config import Settings
from app.extraction.client import (
    ExtractionClient,
    ExtractionServiceUnavailableError,
    MalformedExtractionResponseError,
)


def settings() -> Settings:
    return Settings(neo4j_password="test")


def test_unavailable_model_service_is_clean_error() -> None:
    async def run() -> None:
        def fail(_request):
            raise httpx.ConnectError("offline")

        client = ExtractionClient(settings(), transport=httpx.MockTransport(fail))
        with pytest.raises(ExtractionServiceUnavailableError):
            await client.extract("texto")
        await client.close()

    asyncio.run(run())


def test_malformed_model_output_is_rejected() -> None:
    async def run() -> None:
        client = ExtractionClient(
            settings(),
            transport=httpx.MockTransport(
                lambda _request: httpx.Response(200, json={"unexpected": True})
            ),
        )
        with pytest.raises(MalformedExtractionResponseError):
            await client.extract("texto")
        await client.close()

    asyncio.run(run())
