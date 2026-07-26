"""Verification script to test the Google Health client against a live API sandbox.

Requires the GOOGLE_HEALTH_ACCESS_TOKEN environment variable to be set.
"""

import asyncio
import os
import sys
import uuid
from datetime import UTC, datetime, timedelta

import aiohttp

from google_health_api.api import GoogleHealthApi
from google_health_api.auth import AbstractAuth
from google_health_api.exceptions import GoogleHealthApiError
from google_health_api.model import DataPoint, DataSource
from google_health_api.model.activity import ObservationTimeInterval, Steps


class EnvAuth(AbstractAuth):
    """Auth class that reads access token from environment variables."""

    def __init__(self, websession: aiohttp.ClientSession) -> None:
        """Initialize EnvAuth."""
        super().__init__(websession)
        token = os.environ.get("GOOGLE_HEALTH_ACCESS_TOKEN")
        if not token:
            print("ERROR: GOOGLE_HEALTH_ACCESS_TOKEN environment variable not set.")
            print(
                "Please export a valid Google OAuth2 access token to run this script."
            )
            sys.exit(1)
        self._token = token

    async def async_get_access_token(self) -> str:
        """Return the access token."""
        return self._token


async def verify_profile(api: GoogleHealthApi) -> None:
    """Verify profile retrieval."""
    print("\n=== PROFILE VERIFICATION ===")
    profile = await api.get_profile()
    print("User Profile details:")
    print(f"  Resource Name: {profile.name}")
    print(f"  Age: {profile.age}")
    if profile.membership_start_date:
        d = profile.membership_start_date
        print(f"  Membership Start Date: {d.year}-{d.month:02d}-{d.day:02d}")


async def verify_settings(api: GoogleHealthApi) -> None:
    """Verify settings retrieval."""
    print("\n=== SETTINGS VERIFICATION ===")
    settings = await api.get_settings()
    print("User Settings:")
    print(f"  Resource Name: {settings.name}")
    print(f"  Timezone: {settings.time_zone} (UTC offset: {settings.utc_offset})")
    print(f"  Distance Unit: {settings.distance_unit}")


async def verify_devices(api: GoogleHealthApi) -> None:
    """Verify paired devices retrieval."""
    print("\n=== PAIRED DEVICES VERIFICATION ===")
    result = await api.paired_devices.list(page_size=5)
    print(f"Paired devices found: {len(result.paired_devices)}")
    for device in result.paired_devices:
        print(f"  - {device.device_version} ({device.device_type})")
        print(f"    Name: {device.name}")


async def verify_steps(api: GoogleHealthApi) -> None:
    """Verify listing and creating/deleting step count records."""
    print("\n=== STEPS VERIFICATION ===")
    print("1. Listing steps for the past 7 days...")
    end = datetime.now(UTC)
    start = end - timedelta(days=7)

    list_res = await api.steps.list(start_time=start, end_time=end, page_size=5)
    print(f"   Found {len(list_res.data_points)} data points on first page.")
    for dp in list_res.data_points:
        print(
            f"   - {dp.name}: {dp.data.count} steps ({dp.data.start_time} to {dp.data.end_time})"
        )

    # 2. Reconcile Steps
    print("\n2. Reconciling steps...")
    rec_res = await api.steps.reconcile(start_time=start, end_time=end, page_size=5)
    print(
        f"   Found {len(rec_res.reconciled_data_points)} reconciled data points on first page."
    )

    # 3. Create, Get, and Delete a temporary data point
    print("\n3. Creating temporary step record (120 steps)...")
    now_str = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    future_str = (
        (datetime.now(UTC) + timedelta(minutes=15)).isoformat().replace("+00:00", "Z")
    )

    steps_payload = Steps(
        count=120,
        interval=ObservationTimeInterval(start_time=now_str, end_time=future_str),
    )

    point_id = f"sandbox-test-{uuid.uuid4()}"
    new_dp = DataPoint(
        name=f"users/me/dataTypes/steps/dataPoints/{point_id}",
        data=steps_payload,
        data_source=DataSource(
            platform="GOOGLE_WEB_API",
            recording_method="PASSIVELY_MEASURED",
        ),
    )

    try:
        created_dp = await api.steps.create(new_dp)
        print(f"   Successfully created: {created_dp.name}")

        print(f"\n4. Fetching created data point by ID: {point_id}...")
        fetched_dp = await api.steps.get(point_id)
        print(f"   Retrieved steps: {fetched_dp.data.count}")

        print(f"\n5. Deleting temporary data point: {point_id}...")
        await api.steps.delete(point_id)
        print("   Deleted successfully.")

    except GoogleHealthApiError as ex:
        print(f"   Write operations skipped/failed: {ex}")


async def verify_heart_rate(api: GoogleHealthApi) -> None:
    """Verify listing heart rate records."""
    print("\n=== HEART RATE VERIFICATION ===")
    print("1. Listing heart rate records for the past 7 days...")
    end = datetime.now(UTC)
    start = end - timedelta(days=7)

    list_res = await api.heart_rate.list(start_time=start, end_time=end, page_size=5)
    print(f"   Found {len(list_res.data_points)} data points on first page.")
    for dp in list_res.data_points:
        print(
            f"   - {dp.name}: {dp.data.bpm} bpm ({dp.data.start_time} to {dp.data.end_time})"
        )


async def main() -> None:
    """Run all verification tests."""
    async with aiohttp.ClientSession() as session:
        auth = EnvAuth(session)
        api = GoogleHealthApi(auth)

        try:
            await verify_profile(api)
            await verify_settings(api)
            await verify_devices(api)
            await verify_steps(api)
            await verify_heart_rate(api)
            print("\nVerification completed successfully!")
        except Exception as err:  # noqa: BLE001
            print(f"\nVerification failed with unexpected error: {err}")
            sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
