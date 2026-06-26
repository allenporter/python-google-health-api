"""Example script showing how to list steps using the Google Health API client."""

import asyncio
from datetime import datetime, timezone, timedelta
import aiohttp

from google_health_api.api import GoogleHealthApi
from google_health_api.auth import AbstractAuth


class SimpleAuth(AbstractAuth):
    """Simple authentication implementation holding a static token."""

    def __init__(self, websession: aiohttp.ClientSession, access_token: str) -> None:
        """Initialize authentication wrapper."""
        super().__init__(websession)
        self._access_token = access_token

    async def async_get_access_token(self) -> str:
        """Return the static access token."""
        return self._access_token


async def main() -> None:
    """Run the list steps example."""
    # A placeholder access token. In a real-world app, you would retrieve
    # this using an OAuth 2.0 flow for Google Health scopes.
    access_token = "YOUR_ACCESS_TOKEN"

    async with aiohttp.ClientSession() as session:
        auth = SimpleAuth(session, access_token)
        api = GoogleHealthApi(auth)

        print("Fetching steps for the last 24 hours...")

        # Calculate time range for the last 24 hours
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=1)

        try:
            result = await api.steps.list(
                start_time=start_time,
                end_time=end_time,
                page_size=10,
            )

            if not result.data_points:
                print("No step data points found in the last 24 hours.")
                return

            for point in result.data_points:
                print(f"Data Point Name: {point.name}")
                print(f"  Steps Count: {point.data.count}")
                print(f"  Time Range: {point.data.start_time} -> {point.data.end_time}")
                if point.data_source:
                    print(f"  Source Platform: {point.data_source.platform}")
                print("-" * 40)

        except Exception as err:
            print(f"API call failed: {err}")
            print("Make sure you provide a valid access token and have steps data.")


if __name__ == "__main__":
    asyncio.run(main())
