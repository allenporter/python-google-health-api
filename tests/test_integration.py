"""Live integration tests for Google Health API, executed if token.json is present."""

import json
import os
from datetime import datetime, timedelta, timezone

import aiohttp
import pytest
from google.oauth2.credentials import Credentials

from google_health_api.api import GoogleHealthApi
from google_health_api.auth import AbstractAuth

TOKEN_FILE = "token.json"


class CredentialsAuth(AbstractAuth):
    """Auth wrapper that handles google-auth credentials."""

    def __init__(self, websession: aiohttp.ClientSession, credentials) -> None:
        """Initialize credentials wrapper."""
        super().__init__(websession)
        self._credentials = credentials

    async def async_get_access_token(self) -> str:
        """Retrieve access token, refreshing if necessary."""
        if not self._credentials.valid:
            import asyncio
            from google.auth.transport.requests import Request

            loop = asyncio.get_running_loop()
            req = Request()
            await loop.run_in_executor(None, self._credentials.refresh, req)
            with open(TOKEN_FILE, "w") as f:
                f.write(self._credentials.to_json())
        return self._credentials.token


@pytest.mark.skipif(not os.path.exists(TOKEN_FILE), reason="token.json not present")
@pytest.mark.asyncio
async def test_live_api_integration() -> None:
    """Execute live requests to all key endpoints and assert successful parsing."""
    with open(TOKEN_FILE, "r") as f:
        data = json.load(f)

    creds = Credentials(
        token=data.get("token"),
        refresh_token=data.get("refresh_token"),
        token_uri=data.get("token_uri"),
        client_id=data.get("client_id"),
        client_secret=data.get("client_secret"),
    )

    async with aiohttp.ClientSession() as session:
        auth = CredentialsAuth(session, creds)
        api = GoogleHealthApi(auth)

        # 1. Profile
        profile = await api.get_profile()
        assert profile.name is not None
        print(f"\nLive profile validated: {profile.name}")

        # 2. Settings
        settings = await api.get_settings()
        assert settings.name is not None
        print(f"Live settings validated: {settings.name}")

        # 3. Paired Devices
        devices_res = await api.paired_devices.list(page_size=5)
        assert devices_res.paired_devices is not None
        print(f"Live devices validated: {len(devices_res.paired_devices)} devices")

        # 4. Steps
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=1)
        steps_res = await api.steps.list(start_time=start, end_time=end, page_size=5)
        assert steps_res.data_points is not None
        print(f"Live steps validated: {len(steps_res.data_points)} points")

        # 5. Heart Rate
        hr_res = await api.heart_rate.list(start_time=start, end_time=end, page_size=5)
        assert hr_res.data_points is not None
        print(f"Live heart rate validated: {len(hr_res.data_points)} points")
