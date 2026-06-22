"""Example script showing how to use the OAuth 2.0 Installed App Flow to authenticate.

Requires a `client_secret.json` file downloaded from the Google Cloud Console.
"""

import asyncio
import os
import sys
import aiohttp

from google_health_api.api import GoogleHealthApi
from google_health_api.auth import AbstractAuth
from google_health_api.exceptions import HealthApiException


class CredentialsAuth(AbstractAuth):
    """Auth implementation wrapper that uses google-auth credentials."""

    def __init__(self, websession: aiohttp.ClientSession, credentials) -> None:
        """Initialize CredentialsAuth."""
        super().__init__(websession)
        self._credentials = credentials

    async def async_get_access_token(self) -> str:
        """Return a valid access token, refreshing if necessary."""
        if not self._credentials.valid:
            import asyncio
            from google.auth.transport.requests import Request

            loop = asyncio.get_running_loop()
            req = Request()
            await loop.run_in_executor(None, self._credentials.refresh, req)
        return self._credentials.token


async def main() -> None:
    """Run the OAuth 2.0 Web/Installed flow verification."""
    json_path = "client_secret.json"
    if not os.path.exists(json_path):
        print(f"ERROR: Client secrets file not found at: {json_path}")
        print("\nTo run this example:")
        print("1. Go to the Google Cloud Console.")
        print("2. Create an OAuth 2.0 Client ID with application type 'Desktop application'.")
        print("3. Download the JSON credentials file, rename it to 'client_secret.json',")
        print("   and place it in the root folder of this project.")
        sys.exit(1)

    # Scopes needed for read access to Steps and Heart Rate
    scopes = [
        "https://www.googleapis.com/auth/health.steps.read",
        "https://www.googleapis.com/auth/health.heart-rate.read",
    ]

    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError as err:
        print("ERROR: google-auth-oauthlib is required to run this example.")
        print("Please install the dev dependencies first: uv pip install -r requirements_dev.txt")
        sys.exit(1)

    print("Initializing InstalledAppFlow...")
    flow = InstalledAppFlow.from_client_secrets_file(
        json_path,
        scopes=scopes,
    )

    # This opens a local web browser page to prompt you for authentication and consent
    print("\nRunning local server flow for authentication. Please check your web browser...")
    credentials = flow.run_local_server(port=0)

    print("\nAuthentication successful!")
    print(f"Access Token (preview): {credentials.token[:15]}...{credentials.token[-15:]}")

    async with aiohttp.ClientSession() as session:
        auth = CredentialsAuth(session, credentials)
        api = GoogleHealthApi(auth)

        # 1. Fetch steps for the past 24 hours
        from datetime import datetime, timezone, timedelta
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=1)

        print("\nFetching steps from the last 24 hours...")
        try:
            result = await api.steps.list(start_time=start_time, end_time=end_time, page_size=5)
            print(f"Found {len(result.data_points)} step data points:")
            for point in result.data_points:
                print(f"  - {point.data.count} steps ({point.data.start_time} to {point.data.end_time})")
        except HealthApiException as err:
            print(f"Failed to fetch steps: {err}")

        # 2. Fetch heart rate records
        print("\nFetching heart rate records from the last 24 hours...")
        try:
            hr_result = await api.heart_rate.list(start_time=start_time, end_time=end_time, page_size=5)
            print(f"Found {len(hr_result.data_points)} heart rate data points:")
            for point in hr_result.data_points:
                print(f"  - {point.data.bpm} BPM ({point.data.start_time} to {point.data.end_time})")
        except HealthApiException as err:
            print(f"Failed to fetch heart rate: {err}")


if __name__ == "__main__":
    asyncio.run(main())
