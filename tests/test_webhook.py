"""Tests for Google Health API webhook parsing and mapping."""

import base64
import datetime
from collections.abc import Awaitable, Callable
from unittest.mock import patch

import aiohttp
import pytest
from aiohttp.web import Application, Request, Response, json_response

from google_health_api import model
from google_health_api.exceptions import HealthApiException
from google_health_api.tink import WebhookKeyset
from google_health_api.webhook import WebhookData, WebhookNotification, WebhookVerifier


def test_parse_verification_request() -> None:
    """Test parsing an endpoint verification request payload."""
    payload = {"type": "verification"}
    notification = WebhookNotification.from_dict(payload)
    assert notification.type == "verification"
    assert notification.data is None


def test_parse_data_notification() -> None:
    """Test parsing a real-time data update notification payload."""
    payload = {
        "data": {
            "clientProvidedSubscriptionName": "subscription-uuid-123",
            "healthUserId": "user-uuid-456",
            "dataType": "steps",
            "operation": "UPSERT",
            "civilIso8601TimeInterval": {
                "startTime": "2026-03-07T17:29:00",
                "endTime": "2026-03-07T17:34:00",
            },
        }
    }
    notification = WebhookNotification.from_dict(payload)
    assert notification.type is None
    assert notification.data is not None
    assert (
        notification.data.client_provided_subscription_name == "subscription-uuid-123"
    )
    assert notification.data.health_user_id == "user-uuid-456"
    assert notification.data.data_type_str == "steps"
    assert notification.data.operation == "UPSERT"
    assert notification.data.civil_iso8601_time_interval is not None
    assert (
        notification.data.civil_iso8601_time_interval.start_time
        == "2026-03-07T17:29:00"
    )
    assert (
        notification.data.civil_iso8601_time_interval.end_time == "2026-03-07T17:34:00"
    )

    # Verify resolution to DataType object
    assert notification.data.data_type is model.STEPS
    assert repr(notification.data.data_type) == "<DataType: steps>"


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
    verifier._last_fetched = datetime.datetime.now(datetime.UTC) - datetime.timedelta(
        days=10
    )

    with pytest.raises(
        HealthApiException, match="Failed to fetch Webhook Keyset from network."
    ):
        await verifier._get_keyset()


def test_webhook_data_type_none() -> None:
    """Verify that a missing data type string returns None."""
    data = WebhookData(data_type_str=None)
    assert data.data_type is None


async def test_webhook_verifier_verify_method(
    aiohttp_client: Callable[[Application], Awaitable[aiohttp.ClientSession]],
    keyset_json: dict,
) -> None:
    """Verify that verify() fetches the keyset and calls verify_signature."""
    app = Application()

    async def handler(request: Request) -> Response:
        return json_response(keyset_json)

    app.router.add_get("/keyset", handler)
    client = await aiohttp_client(app)

    verifier = WebhookVerifier(
        websession=client,
        keyset_url="/keyset",
    )

    with patch("google_health_api.tink.WebhookKeyset.verify_signature") as mock_verify:
        await verifier.verify("fake-sig", b"fake-payload")
        mock_verify.assert_called_once_with("fake-sig", b"fake-payload")


async def test_webhook_verifier_verify_method_exception(
    aiohttp_client: Callable[[Application], Awaitable[aiohttp.ClientSession]],
    keyset_json: dict,
) -> None:
    """Verify that verify() wraps KeysetError into WebhookSignatureError."""
    from google_health_api.exceptions import WebhookSignatureError
    from google_health_api.tink import KeysetError

    app = Application()

    async def handler(request: Request) -> Response:
        return json_response(keyset_json)

    app.router.add_get("/keyset", handler)
    client = await aiohttp_client(app)

    verifier = WebhookVerifier(
        websession=client,
        keyset_url="/keyset",
    )

    with patch("google_health_api.tink.WebhookKeyset.verify_signature") as mock_verify:
        mock_verify.side_effect = KeysetError("Mocked failure")
        with pytest.raises(
            WebhookSignatureError, match="Webhook signature verification failed"
        ):
            await verifier.verify("fake-sig", b"fake-payload")


def test_can_use_cache_none() -> None:
    """Verify that _can_use_cache returns False if keyset is empty."""
    verifier = WebhookVerifier(websession=None)  # type: ignore
    now = datetime.datetime.now(datetime.UTC)
    assert not verifier._can_use_cache(now)


async def test_webhook_verifier_empty_cache(
    aiohttp_client: Callable[[Application], Awaitable[aiohttp.ClientSession]],
    keyset_json: dict,
) -> None:
    """Verify that if the fetch returns no valid keyset, it raises HealthApiException."""
    app = Application()

    async def handler(request: Request) -> Response:
        return json_response(keyset_json)

    app.router.add_get("/keyset", handler)
    client = await aiohttp_client(app)

    verifier = WebhookVerifier(
        websession=client,
        keyset_url="/keyset",
    )

    with (
        patch("google_health_api.tink.WebhookKeyset.from_dict", return_value=None),
        pytest.raises(HealthApiException, match="Keyset is not available."),
    ):
        await verifier._get_keyset()
