"""Tests for user profile, settings, and paired devices API endpoints."""

from collections.abc import AsyncGenerator
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from google_health_api.api import GoogleHealthApi
from google_health_api.exceptions import (
    HealthApiForbiddenException,
    HealthApiServiceDisabledException,
)
from google_health_api.model import (
    Date,
    Profile,
    Settings,
)

from .conftest import AuthCallback

FAKE_PROFILE_PAYLOAD = {
    "name": "users/me/profile",
    "age": 35,
    "membershipStartDate": {"year": 2026, "month": 6, "day": 22},
    "userConfiguredWalkingStrideLengthMm": 750,
    "autoWalkingStrideLengthMm": 762,
}

FAKE_IDENTITY_PAYLOAD = {
    "name": "users/me/identity",
    "healthUserId": "health-id-123",
    "legacyUserId": "fitbit-id-abc",
}

FAKE_SETTINGS_PAYLOAD = {
    "name": "users/me/settings",
    "waterUnit": "WATER_UNIT_ML",
    "weightUnit": "WEIGHT_UNIT_KILOGRAMS",
    "timeZone": "America/New_York",
}

FAKE_IRN_PROFILE_PAYLOAD = {
    "name": "users/me/irnProfile",
    "onboardingStatus": True,
    "enrollmentStatus": True,
    "updateTime": "2026-06-22T08:00:00Z",
}

FAKE_PAIRED_DEVICE_PAYLOAD = {
    "name": "users/me/pairedDevices/device-123",
    "macAddress": "00:11:22:33:44:55",
    "deviceType": "TRACKER",
    "features": ["STEPS", "HEART_RATE"],
    "lastSyncTime": "2026-06-22T08:05:00Z",
    "batteryStatus": "High",
    "batteryLevel": 85,
    "deviceVersion": "Charge 6",
}


@pytest.fixture(name="api_responses")
def mock_api_responses() -> dict[str, list[dict[str, Any]]]:
    """Fixture for tracking mock responses by path/method key."""
    return {
        "profile_get": [],
        "profile_patch": [],
        "identity_get": [],
        "settings_get": [],
        "settings_patch": [],
        "irn_get": [],
        "device_list": [],
        "device_get": [],
    }


@pytest.fixture(name="requests")
def mock_requests() -> list[dict[str, Any]]:
    """Fixture for capturing requests."""
    return []


@pytest.fixture(name="api")
async def mock_api(
    auth_cb: AuthCallback,
    requests: list[dict[str, Any]],
    api_responses: dict[str, list[dict[str, Any]]],
) -> AsyncGenerator[GoogleHealthApi]:
    """Fixture to create the mock GoogleHealthApi client with profile endpoints."""

    async def get_profile_handler(request: aiohttp.web.Request) -> aiohttp.web.Response:
        requests.append({"method": "GET", "url": str(request.url)})
        return aiohttp.web.json_response(api_responses["profile_get"].pop(0))

    async def patch_profile_handler(
        request: aiohttp.web.Request,
    ) -> aiohttp.web.Response:
        body = await request.json()
        requests.append(
            {
                "method": "PATCH",
                "url": str(request.url),
                "body": body,
                "query": dict(request.query),
            }
        )
        return aiohttp.web.json_response(api_responses["profile_patch"].pop(0))

    async def get_identity_handler(
        request: aiohttp.web.Request,
    ) -> aiohttp.web.Response:
        requests.append({"method": "GET", "url": str(request.url)})
        return aiohttp.web.json_response(api_responses["identity_get"].pop(0))

    async def get_settings_handler(
        request: aiohttp.web.Request,
    ) -> aiohttp.web.Response:
        requests.append({"method": "GET", "url": str(request.url)})
        return aiohttp.web.json_response(api_responses["settings_get"].pop(0))

    async def patch_settings_handler(
        request: aiohttp.web.Request,
    ) -> aiohttp.web.Response:
        body = await request.json()
        requests.append(
            {
                "method": "PATCH",
                "url": str(request.url),
                "body": body,
                "query": dict(request.query),
            }
        )
        return aiohttp.web.json_response(api_responses["settings_patch"].pop(0))

    async def get_irn_handler(request: aiohttp.web.Request) -> aiohttp.web.Response:
        requests.append({"method": "GET", "url": str(request.url)})
        return aiohttp.web.json_response(api_responses["irn_get"].pop(0))

    async def list_devices_handler(
        request: aiohttp.web.Request,
    ) -> aiohttp.web.Response:
        requests.append(
            {"method": "GET", "url": str(request.url), "query": dict(request.query)}
        )
        return aiohttp.web.json_response(api_responses["device_list"].pop(0))

    async def get_device_handler(request: aiohttp.web.Request) -> aiohttp.web.Response:
        requests.append({"method": "GET", "url": str(request.url)})
        return aiohttp.web.json_response(api_responses["device_get"].pop(0))

    auth = await auth_cb(
        [
            ("GET", "v4/users/{user}/profile", get_profile_handler),
            ("PATCH", "v4/users/{user}/profile", patch_profile_handler),
            ("GET", "v4/users/{user}/identity", get_identity_handler),
            ("GET", "v4/users/{user}/settings", get_settings_handler),
            ("PATCH", "v4/users/{user}/settings", patch_settings_handler),
            ("GET", "v4/users/{user}/irnProfile", get_irn_handler),
            ("GET", "v4/users/{user}/pairedDevices", list_devices_handler),
            (
                "GET",
                "v4/users/{user}/pairedDevices/{pairedDevicesId}",
                get_device_handler,
            ),
        ]
    )

    yield GoogleHealthApi(auth)


async def test_get_profile(
    api: GoogleHealthApi,
    api_responses: dict[str, list[dict[str, Any]]],
    requests: list[dict[str, Any]],
) -> None:
    """Test retrieving user profile."""
    api_responses["profile_get"].append(FAKE_PROFILE_PAYLOAD)

    profile = await api.get_profile()
    assert profile.name == "users/me/profile"
    assert profile.age == 35
    assert profile.membership_start_date == Date(year=2026, month=6, day=22)
    assert profile.user_configured_walking_stride_length_mm == 750
    assert profile.auto_walking_stride_length_mm == 762

    assert len(requests) == 1
    assert requests[0]["method"] == "GET"
    assert requests[0]["url"].endswith("/profile")


async def test_update_profile(
    api: GoogleHealthApi,
    api_responses: dict[str, list[dict[str, Any]]],
    requests: list[dict[str, Any]],
) -> None:
    """Test updating user profile details."""
    api_responses["profile_patch"].append(FAKE_PROFILE_PAYLOAD)

    update_profile = Profile(
        name="users/me/profile",
        age=36,
        user_configured_walking_stride_length_mm=755,
    )
    profile = await api.update_profile(
        update_profile, update_mask="age,userConfiguredWalkingStrideLengthMm"
    )
    assert profile.age == 35  # mock returns payload

    assert len(requests) == 1
    assert requests[0]["method"] == "PATCH"
    assert requests[0]["body"]["age"] == 36
    assert requests[0]["body"]["userConfiguredWalkingStrideLengthMm"] == 755
    assert (
        requests[0]["query"]["updateMask"] == "age,userConfiguredWalkingStrideLengthMm"
    )


async def test_get_identity(
    api: GoogleHealthApi,
    api_responses: dict[str, list[dict[str, Any]]],
    requests: list[dict[str, Any]],
) -> None:
    """Test retrieving user identity mapping."""
    api_responses["identity_get"].append(FAKE_IDENTITY_PAYLOAD)

    identity = await api.get_identity()
    assert identity.name == "users/me/identity"
    assert identity.health_user_id == "health-id-123"
    assert identity.legacy_user_id == "fitbit-id-abc"

    assert len(requests) == 1
    assert requests[0]["method"] == "GET"
    assert requests[0]["url"].endswith("/identity")


async def test_get_settings(
    api: GoogleHealthApi,
    api_responses: dict[str, list[dict[str, Any]]],
    requests: list[dict[str, Any]],
) -> None:
    """Test retrieving user settings."""
    api_responses["settings_get"].append(FAKE_SETTINGS_PAYLOAD)

    settings = await api.get_settings()
    assert settings.name == "users/me/settings"
    assert settings.water_unit == "WATER_UNIT_ML"
    assert settings.weight_unit == "WEIGHT_UNIT_KILOGRAMS"
    assert settings.time_zone == "America/New_York"

    assert len(requests) == 1
    assert requests[0]["method"] == "GET"
    assert requests[0]["url"].endswith("/settings")


async def test_update_settings(
    api: GoogleHealthApi,
    api_responses: dict[str, list[dict[str, Any]]],
    requests: list[dict[str, Any]],
) -> None:
    """Test updating user settings."""
    api_responses["settings_patch"].append(FAKE_SETTINGS_PAYLOAD)

    update_settings = Settings(
        name="users/me/settings",
        water_unit="WATER_UNIT_FL_OZ",
    )
    settings = await api.update_settings(update_settings, update_mask="waterUnit")
    assert settings.water_unit == "WATER_UNIT_ML"  # Mock returns default payload

    assert len(requests) == 1
    assert requests[0]["method"] == "PATCH"
    assert requests[0]["body"]["waterUnit"] == "WATER_UNIT_FL_OZ"
    assert requests[0]["query"]["updateMask"] == "waterUnit"


async def test_get_irn_profile(
    api: GoogleHealthApi,
    api_responses: dict[str, list[dict[str, Any]]],
    requests: list[dict[str, Any]],
) -> None:
    """Test retrieving user IRN profile."""
    api_responses["irn_get"].append(FAKE_IRN_PROFILE_PAYLOAD)

    irn_profile = await api.get_irn_profile()
    assert irn_profile.name == "users/me/irnProfile"
    assert irn_profile.onboarding_status is True
    assert irn_profile.enrollment_status is True
    assert irn_profile.update_time == "2026-06-22T08:00:00Z"

    assert len(requests) == 1
    assert requests[0]["method"] == "GET"
    assert requests[0]["url"].endswith("/irnProfile")


async def test_list_paired_devices(
    api: GoogleHealthApi,
    api_responses: dict[str, list[dict[str, Any]]],
    requests: list[dict[str, Any]],
) -> None:
    """Test listing user paired devices."""
    api_responses["device_list"].append(
        {
            "pairedDevices": [FAKE_PAIRED_DEVICE_PAYLOAD],
            "nextPageToken": "device-token-xyz",
        }
    )

    result = await api.paired_devices.list(page_size=5)
    assert len(result.paired_devices) == 1
    assert result.next_page_token == "device-token-xyz"

    device = result.paired_devices[0]
    assert device.name == "users/me/pairedDevices/device-123"
    assert device.mac_address == "00:11:22:33:44:55"
    assert device.device_type == "TRACKER"
    assert device.features == ["STEPS", "HEART_RATE"]
    assert device.last_sync_time == "2026-06-22T08:05:00Z"
    assert device.battery_status == "High"
    assert device.battery_level == 85
    assert device.device_version == "Charge 6"

    assert len(requests) == 1
    assert requests[0]["method"] == "GET"
    assert requests[0]["query"]["pageSize"] == "5"


async def test_get_paired_device(
    api: GoogleHealthApi,
    api_responses: dict[str, list[dict[str, Any]]],
    requests: list[dict[str, Any]],
) -> None:
    """Test retrieving specific user paired device."""
    api_responses["device_get"].append(FAKE_PAIRED_DEVICE_PAYLOAD)

    device = await api.paired_devices.get("device-123")
    assert device.name == "users/me/pairedDevices/device-123"
    assert device.device_id == "device-123"
    assert device.device_version == "Charge 6"

    assert len(requests) == 1
    assert requests[0]["method"] == "GET"
    assert requests[0]["url"].endswith("/pairedDevices/device-123")


async def test_get_user_info(api: GoogleHealthApi) -> None:
    """Test retrieving OAuth2 userinfo details."""
    fake_userinfo = {
        "sub": "110248495921238986420",
        "name": "John Doe",
        "given_name": "John",
        "family_name": "Doe",
        "picture": "https://lh3.googleusercontent.com/a-/AOh14Gg...",
        "email": "johndoe@example.com",
        "email_verified": True,
        "locale": "en",
    }

    with patch.object(api._session, "get", new_callable=AsyncMock) as mock_get:
        mock_resp = MagicMock()
        mock_resp.json = AsyncMock(return_value=fake_userinfo)
        mock_get.return_value = mock_resp

        user_info = await api.get_user_info()
        assert user_info.sub == "110248495921238986420"
        assert user_info.name == "John Doe"
        assert user_info.given_name == "John"
        assert user_info.family_name == "Doe"
        assert user_info.picture == "https://lh3.googleusercontent.com/a-/AOh14Gg..."
        assert user_info.email == "johndoe@example.com"
        assert user_info.email_verified is True
        assert user_info.locale == "en"
        assert user_info.display_name == "John Doe"

        mock_get.assert_called_once_with(
            "https://www.googleapis.com/oauth2/v3/userinfo"
        )


async def test_get_user_info_service_disabled(api: GoogleHealthApi) -> None:
    """Test get_user_info error propagation when service is disabled."""
    with patch.object(
        api._session,
        "get",
        side_effect=HealthApiServiceDisabledException("Service disabled"),
    ):
        with pytest.raises(HealthApiServiceDisabledException) as exc_info:
            await api.get_user_info()

        assert isinstance(exc_info.value, HealthApiForbiddenException)
