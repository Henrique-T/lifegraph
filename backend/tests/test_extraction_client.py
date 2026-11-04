"""Unit tests for extraction-service error handling."""

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
    """Create a settings fixture for the test."""
    return Settings(neo4j_password="test")


def test_unavailable_model_service_is_clean_error() -> None:
    """Verify unavailable model service is clean error."""
    async def run() -> None:
        """Run the asynchronous test scenario."""
        def fail(_request):
            """Provide the test fail callback."""
            raise httpx.ConnectError("offline")

        client = ExtractionClient(settings(), transport=httpx.MockTransport(fail))
        with pytest.raises(ExtractionServiceUnavailableError):
            await client.extract("texto")
        await client.close()

    asyncio.run(run())


def test_malformed_model_output_is_rejected() -> None:
    """Verify malformed model output is rejected."""
    async def run() -> None:
        """Run the asynchronous test scenario."""
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
