"""Example script showing how to use ServiceAccountAuth with a service account key file."""

import asyncio
import os
import sys
import aiohttp

from google_health_api.api import GoogleHealthApi
from google_health_api.auth import AbstractAuth
from google_health_api.const import HealthApiScope
from google_health_api.exceptions import HealthApiException


class ServiceAccountAuth(AbstractAuth):
    """Authentication using a Google Service Account key file."""

    def __init__(
        self,
        websession: aiohttp.ClientSession,
        json_path: str,
        subject: str | None = None,
        scopes: list[str] | None = None,
        host: str | None = None,
    ) -> None:
        """Initialize ServiceAccountAuth."""
        super().__init__(websession, host)
        from google.oauth2 import service_account

        if scopes is None:
            scopes = [
                HealthApiScope.ACTIVITY_READ,
                HealthApiScope.ACTIVITY_WRITE,
                HealthApiScope.MEASUREMENTS_READ,
                HealthApiScope.MEASUREMENTS_WRITE,
            ]

        self._credentials = service_account.Credentials.from_service_account_file(
            json_path,
            scopes=scopes,
            subject=subject,
        )

    async def async_get_access_token(self) -> str:
        """Fetch and return a valid access token."""
        import asyncio
        from google.auth.transport.requests import Request

        loop = asyncio.get_running_loop()
        req = Request()
        await loop.run_in_executor(None, self._credentials.refresh, req)
        return self._credentials.token


async def main() -> None:
    """Run the service account auth example."""
    json_path = "service_account.json"
    if not os.path.exists(json_path):
        print(f"ERROR: Service account JSON file not found at: {json_path}")
        print("Please place your service account JSON file in the project root.")
        sys.exit(1)

    # If domain-wide delegation is configured, provide the email address of the user
    # you wish to impersonate. If accessing Cloud Healthcare or similar, leave as None.
    # We will try to read from the environment variable if present.
    subject_email = os.environ.get("GOOGLE_HEALTH_SUBJECT_EMAIL")

    async with aiohttp.ClientSession() as session:
        scopes = None
        if not subject_email:
            print(
                "No GOOGLE_HEALTH_SUBJECT_EMAIL provided. Requesting standard GCP userinfo.email scope for verification..."
            )
            scopes = ["https://www.googleapis.com/auth/userinfo.email"]

        auth = ServiceAccountAuth(
            websession=session,
            json_path=json_path,
            subject=subject_email,
            scopes=scopes,
        )

        print("Requesting access token from Google's OAuth 2.0 endpoints...")
        try:
            token = await auth.async_get_access_token()
            print("Successfully retrieved access token!")
            # Truncate token print for security
            print(f"Token (preview): {token[:15]}...{token[-15:]}")
        except Exception as err:
            print(f"Failed to fetch access token: {err}")
            sys.exit(1)

        api = GoogleHealthApi(auth)

        # Determine the user ID to pass to requests (defaults to 'me' if not impersonating)
        user_id = subject_email if subject_email else "me"
        print(f"\nListing steps for user '{user_id}'...")

        try:
            result = await api.steps.list(page_size=5, user=user_id)
            print(f"Found {len(result.data_points)} step data points on first page.")
            for point in result.data_points:
                print(
                    f"  - {point.name}: {point.data.count} steps ({point.data.start_time} to {point.data.end_time})"
                )
        except HealthApiException as err:
            print(f"API request failed: {err}")
            print(
                "\nNote: Standard consumer Google Health metrics cannot be accessed directly by a service"
            )
            print(
                "account itself. A service account requires Google Workspace domain-wide delegation to"
            )
            print(
                "impersonate a user (by setting the GOOGLE_HEALTH_SUBJECT_EMAIL environment variable)."
            )


if __name__ == "__main__":
    asyncio.run(main())
