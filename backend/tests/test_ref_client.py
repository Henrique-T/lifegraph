"""Unit tests for the read-only REF HTTP client."""

import asyncio
import json
from uuid import UUID

import httpx
import pytest

from app.core.config import Settings
from app.ref.client import (
    RefAuthenticationError,
    RefClient,
    RefMalformedResponseError,
    RefPersonNotFoundError,
    RefUnavailableError,
)

PERSON_ID = UUID("73bacb7c-2806-457a-b910-62d93a4b9959")


def test_lists_ref_people_with_explicit_limit_and_bearer_token() -> None:
    """Verify lists ref people with explicit limit and bearer token."""
    asyncio.run(_test_lists_ref_people_with_explicit_limit_and_bearer_token())


async def _test_lists_ref_people_with_explicit_limit_and_bearer_token() -> None:
    """Run the asynchronous ists ref people with explicit limit and bearer token scenario."""
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        """Provide the test handler callback."""
        seen.append(request)
        return httpx.Response(200, json=[{
            "id_pessoa": str(PERSON_ID),
            "cpn": "A1B2C3O",
            "nome": "Pessoa de Teste",
            "cpf": None,
            "data_nascimento": "1990-01-01",
            "sexo": "F",
        }])

    client = RefClient(settings(), transport=httpx.MockTransport(handler))
    try:
        people = await client.list_people(50)
    finally:
        await client.close()

    assert people[0].id_pessoa == PERSON_ID
    assert people[0].nome == "Pessoa de Teste"
    assert len(seen) == 1
    assert seen[0].url.path == "/pessoas/recent"
    assert seen[0].url.params["limit"] == "50"
    assert seen[0].headers["Authorization"] == "Bearer test-token"


def test_maps_ref_people_authentication_failure() -> None:
    """Verify maps ref people authentication failure."""
    asyncio.run(_test_maps_ref_people_authentication_failure())


async def _test_maps_ref_people_authentication_failure() -> None:
    """Run the asynchronous aps ref people authentication failure scenario."""
    client = RefClient(
        settings(), transport=httpx.MockTransport(lambda _request: httpx.Response(401))
    )
    with pytest.raises(RefAuthenticationError):
        await client.list_people()
    await client.close()


def test_rejects_malformed_ref_person_list() -> None:
    """Verify rejects malformed ref person list."""
    asyncio.run(_test_rejects_malformed_ref_person_list())


async def _test_rejects_malformed_ref_person_list() -> None:
    """Run the asynchronous ejects malformed ref person list scenario."""
    client = RefClient(
        settings(), transport=httpx.MockTransport(
            lambda _request: httpx.Response(200, json=[{"nome": "Sem identificador"}])
        )
    )
    with pytest.raises(RefMalformedResponseError):
        await client.list_people()
    await client.close()


def settings() -> Settings:
    """Create a settings fixture for the test."""
    return Settings(neo4j_password="test", ref_bearer_token="test-token")


def test_parses_verified_trail_and_uses_only_canonical_get_path() -> None:
    """Verify parses verified trail and uses only canonical get path."""
    asyncio.run(_test_parses_verified_trail_and_uses_only_canonical_get_path())


async def _test_parses_verified_trail_and_uses_only_canonical_get_path() -> None:
    """Run the asynchronous arses verified trail and uses only canonical get path scenario."""
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        """Provide the test handler callback."""
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
    """Verify rejects malformed trail."""
    asyncio.run(_test_rejects_malformed_trail())


async def _test_rejects_malformed_trail() -> None:
    """Run the asynchronous ejects malformed trail scenario."""
    transport = httpx.MockTransport(
        lambda _request: httpx.Response(200, content=json.dumps([{"tipo": "obito"}]))
    )
    client = RefClient(settings(), transport=transport)
    with pytest.raises(RefMalformedResponseError):
        await client.get_person_trail(PERSON_ID)
    await client.close()


def test_maps_ref_404() -> None:
    """Verify maps ref 404."""
    asyncio.run(_test_maps_ref_404())


async def _test_maps_ref_404() -> None:
    """Run the asynchronous aps ref 404 scenario."""
    client = RefClient(
        settings(), transport=httpx.MockTransport(lambda _request: httpx.Response(404))
    )
    with pytest.raises(RefPersonNotFoundError):
        await client.get_person_trail(PERSON_ID)
    await client.close()


def test_maps_ref_unavailable() -> None:
    """Verify maps ref unavailable."""
    asyncio.run(_test_maps_ref_unavailable())


async def _test_maps_ref_unavailable() -> None:
    """Run the asynchronous aps ref unavailable scenario."""
    def fail(_request: httpx.Request) -> httpx.Response:
        """Provide the test fail callback."""
        raise httpx.ConnectError("offline")

    client = RefClient(settings(), transport=httpx.MockTransport(fail))
    with pytest.raises(RefUnavailableError):
        await client.get_person_trail(PERSON_ID)
    await client.close()
