import asyncio
import json
from uuid import UUID

import httpx
import pytest

from app.core.config import Settings
from app.ref.client import (
    RefClient,
    RefMalformedResponseError,
    RefPersonNotFoundError,
    RefUnavailableError,
)

PERSON_ID = UUID("73bacb7c-2806-457a-b910-62d93a4b9959")


def settings() -> Settings:
    return Settings(neo4j_password="test", ref_bearer_token="test-token")


def test_parses_verified_trail_and_uses_only_canonical_get_path() -> None:
    asyncio.run(_test_parses_verified_trail_and_uses_only_canonical_get_path())


async def _test_parses_verified_trail_and_uses_only_canonical_get_path() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(
            200,
            json=[
                {
                    "id_ato": "fef7fa98-7aec-44fe-9caf-fd63c713ad21",
                    "tipo": "nascimento",
                    "papel": "registrando",
                    "data_evento": "2026-07-21T03:00:00Z",
                    "data_registro": "2026-09-02T17:33:00.379930Z",
                    "ignored_extra": "safe",
                }
            ],
        )

    client = RefClient(settings(), transport=httpx.MockTransport(handler))
    try:
        trail = await client.get_person_trail(PERSON_ID)
    finally:
        await client.close()
    assert trail[0].papel == "registrando"
    assert len(seen) == 1
    assert seen[0].method == "GET"
    assert seen[0].url.path == f"/pessoas/{PERSON_ID}/trilha"
    assert len(seen[0].url.params) == 0


def test_rejects_malformed_trail() -> None:
    asyncio.run(_test_rejects_malformed_trail())


async def _test_rejects_malformed_trail() -> None:
    transport = httpx.MockTransport(
        lambda _request: httpx.Response(200, content=json.dumps([{"tipo": "obito"}]))
    )
    client = RefClient(settings(), transport=transport)
    with pytest.raises(RefMalformedResponseError):
        await client.get_person_trail(PERSON_ID)
    await client.close()


def test_maps_ref_404() -> None:
    asyncio.run(_test_maps_ref_404())


async def _test_maps_ref_404() -> None:
    client = RefClient(
        settings(), transport=httpx.MockTransport(lambda _request: httpx.Response(404))
    )
    with pytest.raises(RefPersonNotFoundError):
        await client.get_person_trail(PERSON_ID)
    await client.close()


def test_maps_ref_unavailable() -> None:
    asyncio.run(_test_maps_ref_unavailable())


async def _test_maps_ref_unavailable() -> None:
    def fail(_request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("offline")

    client = RefClient(settings(), transport=httpx.MockTransport(fail))
    with pytest.raises(RefUnavailableError):
        await client.get_person_trail(PERSON_ID)
    await client.close()
