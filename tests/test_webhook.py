"""Tests for the WebhookVerifier."""

import base64
import datetime
from collections.abc import Awaitable, Callable

import aiohttp
import pytest
from aiohttp.web import Application, Request, Response, json_response

from google_health_api.tink import WebhookKeyset, _HAS_CRYPTOGRAPHY
from google_health_api.webhook import WebhookVerifier

if not _HAS_CRYPTOGRAPHY:
    pytest.skip(
        "Cryptography library is required for webhook tests", allow_module_level=True
    )


@pytest.fixture
def keyset_json() -> dict:
    """Returns a valid Google Tink JSON keyset payload."""
    # A minimal valid keyset payload for testing
    return {
        "primaryKeyId": 12345,
        "key": [
            {
                "keyData": {
                    "typeUrl": "type.googleapis.com/google.crypto.tink.EcdsaPublicKey",
                    "value": base64.b64encode(
                        # Encoded dummy protobuf for EcdsaPublicKey
                        b"\x1a\x20" + (b"A" * 32) + b"\x22\x20" + (b"B" * 32)
                    ).decode("ascii"),
                    "keyMaterialType": "ASYMMETRIC_PUBLIC",
                },
                "status": "ENABLED",
                "keyId": 12345,
                "outputPrefixType": "TINK",
            }
        ],
    }


async def test_webhook_verifier_success(
    aiohttp_client: Callable[[Application], Awaitable[aiohttp.ClientSession]],
    keyset_json: dict,
) -> None:
    """Verify that the verifier correctly fetches and parses the keyset."""
    app = Application()

    async def handler(request: Request) -> Response:
        return json_response(keyset_json)

    app.router.add_get("/keyset", handler)
    client = await aiohttp_client(app)

    verifier = WebhookVerifier(
        websession=client,
        keyset_url="/keyset",
    )

    keyset = await verifier._get_keyset()
    assert keyset.primary_key_id == 12345
    assert len(keyset.key) == 1


async def test_webhook_verifier_caching(
    aiohttp_client: Callable[[Application], Awaitable[aiohttp.ClientSession]],
    keyset_json: dict,
) -> None:
    """Verify that multiple calls within the refresh interval use the cache."""
    app = Application()
    request_count = 0

    async def handler(request: Request) -> Response:
        nonlocal request_count
        request_count += 1
        return json_response(keyset_json)

    app.router.add_get("/keyset", handler)
    client = await aiohttp_client(app)

    verifier = WebhookVerifier(
        websession=client,
        keyset_url="/keyset",
        refresh_interval=datetime.timedelta(days=1),
    )

    await verifier._get_keyset()
    assert request_count == 1

    await verifier._get_keyset()
    assert request_count == 1


async def test_webhook_verifier_fallback(
    aiohttp_client: Callable[[Application], Awaitable[aiohttp.ClientSession]],
    keyset_json: dict,
) -> None:
    """Verify that the verifier falls back to the cache if the refresh network call fails."""
    app = Application()
    should_fail = False

    async def handler(request: Request) -> Response:
        if should_fail:
            return Response(status=500)
        return json_response(keyset_json)

    app.router.add_get("/keyset", handler)
    client = await aiohttp_client(app)

    verifier = WebhookVerifier(
        websession=client,
        keyset_url="/keyset",
        refresh_interval=datetime.timedelta(seconds=0),
        max_cache_lifetime=datetime.timedelta(days=7),
    )

    keyset1 = await verifier._get_keyset()
    assert keyset1.primary_key_id == 12345

    should_fail = True

    keyset2 = await verifier._get_keyset()
    assert keyset2 is keyset1


async def test_webhook_verifier_hard_expire(
    aiohttp_client: Callable[[Application], Awaitable[aiohttp.ClientSession]],
    keyset_json: dict,
) -> None:
    """Verify that the verifier raises an error if the network fails and the cache is completely expired."""
    app = Application()

    async def handler(request: Request) -> Response:
        return Response(status=500)

    app.router.add_get("/keyset", handler)
    client = await aiohttp_client(app)

    verifier = WebhookVerifier(
        websession=client,
        keyset_url="/keyset",
    )

    verifier._cached_keyset = WebhookKeyset.from_dict(keyset_json)
    verifier._last_fetched = datetime.datetime.now(
        datetime.timezone.utc
    ) - datetime.timedelta(days=10)

    with pytest.raises(
        RuntimeError, match="Failed to fetch Webhook Keyset and no valid cache exists"
    ):
        await verifier._get_keyset()
