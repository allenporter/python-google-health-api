"""Command-line interface example for the Google Health API.

Supports logging in via browser, listing steps, and listing heart rate.
"""

import argparse
import asyncio
import json
import os
import sys
from datetime import UTC, datetime, timedelta

import aiohttp
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow, InstalledAppFlow

from google_health_api.api import GoogleHealthApi
from google_health_api.auth import AbstractAuth
from google_health_api.const import HealthApiScope
from google_health_api.exceptions import HealthApiException

TOKEN_FILE = "token.json"
CLIENT_SECRET_FILE = "client_secret.json"
SCOPES = [
    HealthApiScope.ACTIVITY_READ,
    HealthApiScope.MEASUREMENTS_READ,
    HealthApiScope.PROFILE_READ,
    HealthApiScope.SETTINGS_READ,
]


class CredentialsAuth(AbstractAuth):
    """Auth implementation wrapper that uses google-auth credentials."""

    def __init__(self, websession: aiohttp.ClientSession, credentials) -> None:
        """Initialize CredentialsAuth."""
        super().__init__(websession)
        self._credentials = credentials

    async def async_get_access_token(self) -> str:
        """Return a valid access token, refreshing if necessary."""
        if not self._credentials.valid:
            loop = asyncio.get_running_loop()
            req = Request()
            await loop.run_in_executor(None, self._credentials.refresh, req)
            save_credentials(self._credentials)
        return self._credentials.token


def load_credentials():
    """Load credentials from local token file."""
    if not os.path.exists(TOKEN_FILE):
        return None

    with open(TOKEN_FILE, "r") as f:
        data = json.load(f)

    return Credentials(
        token=data.get("token"),
        refresh_token=data.get("refresh_token"),
        token_uri=data.get("token_uri"),
        client_id=data.get("client_id"),
        client_secret=data.get("client_secret"),
        scopes=SCOPES,
    )


def save_credentials(credentials):
    """Save credentials to local token file."""
    with open(TOKEN_FILE, "w") as f:
        f.write(credentials.to_json())


def cmd_login(args) -> None:
    """Run OAuth Web Flow and save token."""
    if not os.path.exists(CLIENT_SECRET_FILE):
        print(f"ERROR: Client secrets file '{CLIENT_SECRET_FILE}' not found.")
        print("\nTo log in:")
        print("1. Go to the Google Cloud Console.")
        print(
            "2. Create an OAuth 2.0 Client ID (type 'Desktop application' or 'Web application')."
        )
        print(
            "3. Download the JSON credentials file, rename it to 'client_secret.json',"
        )
        print("   and place it in the root folder of this project.")
        sys.exit(1)

    with open(CLIENT_SECRET_FILE, "r") as f:
        client_secrets_data = json.load(f)

    is_web = "web" in client_secrets_data

    if is_web:
        redirect_uris = client_secrets_data["web"].get("redirect_uris", [])
        redirect_uri = redirect_uris[0] if redirect_uris else "http://localhost:8080/"

        print("Initializing Flow for Web Application...")
        flow = Flow.from_client_secrets_file(
            CLIENT_SECRET_FILE,
            scopes=SCOPES,
            redirect_uri=redirect_uri,
        )
        authorization_url, _ = flow.authorization_url(
            access_type="offline",
            prompt="consent",
        )
        print("\nWeb-based authentication flow:")
        print("1. Open the following URL in your browser to authorize:")
        print(f"   {authorization_url}")
        print("\n2. Sign in, authorize, and submit.")
        print(
            f"3. Copy the URL of the redirected page (e.g. page matching redirect URI {redirect_uri})"
        )
        print("   from the browser's address bar and paste it below.")

        redirect_response = input("\nRedirected URL (or authorization code): ").strip()

        if not redirect_response:
            print("ERROR: Redirected URL cannot be empty.")
            sys.exit(1)

        os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
        os.environ["OAUTHLIB_RELAX_TOKEN_SCOPE"] = "1"

        if "code=" in redirect_response or redirect_response.startswith("http"):
            flow.fetch_token(authorization_response=redirect_response)
        else:
            flow.fetch_token(code=redirect_response)

        credentials = flow.credentials
    else:
        print("Initializing InstalledAppFlow for Desktop Application...")
        flow = InstalledAppFlow.from_client_secrets_file(
            CLIENT_SECRET_FILE,
            scopes=SCOPES,
        )
        print("\nOpening web browser for authentication. Please approve consent...")
        credentials = flow.run_local_server(port=0)

    save_credentials(credentials)
    print("Successfully logged in and saved credentials to token.json!")


async def run_steps_list(args) -> None:
    """List steps from the API."""
    creds = load_credentials()
    if not creds:
        print(
            "ERROR: Not logged in. Please run `python examples/google_health_cli.py login` first."
        )
        sys.exit(1)

    async with aiohttp.ClientSession() as session:
        auth = CredentialsAuth(session, creds)
        api = GoogleHealthApi(auth)

        end_time = datetime.now(UTC)
        start_time = end_time - timedelta(days=args.days)

        print(f"Fetching steps from the last {args.days} days...")
        try:
            result = await api.steps.list(
                start_time=start_time,
                end_time=end_time,
                page_size=args.limit,
            )
            print(f"\nFound {len(result.data_points)} step data points:")
            for point in result.data_points:
                print(
                    f"  - {point.data.count} steps ({point.data.start_time} to {point.data.end_time})"
                )
        except HealthApiException as err:
            print(f"Failed to fetch steps: {err}")


async def run_heart_rate_list(args) -> None:
    """List heart rate from the API."""
    creds = load_credentials()
    if not creds:
        print(
            "ERROR: Not logged in. Please run `python examples/google_health_cli.py login` first."
        )
        sys.exit(1)

    async with aiohttp.ClientSession() as session:
        auth = CredentialsAuth(session, creds)
        api = GoogleHealthApi(auth)

        end_time = datetime.now(UTC)
        start_time = end_time - timedelta(days=args.days)

        print(f"Fetching heart rate records from the last {args.days} days...")
        try:
            result = await api.heart_rate.list(
                start_time=start_time,
                end_time=end_time,
                page_size=args.limit,
            )
            print(f"\nFound {len(result.data_points)} heart rate data points:")
            for point in result.data_points:
                print(
                    f"  - {point.data.bpm} BPM ({point.data.start_time} to {point.data.end_time})"
                )
        except HealthApiException as err:
            print(f"Failed to fetch heart rate: {err}")


async def run_profile_get(args) -> None:
    """Retrieve and display user profile details."""
    creds = load_credentials()
    if not creds:
        print(
            "ERROR: Not logged in. Please run `python examples/google_health_cli.py login` first."
        )
        sys.exit(1)

    async with aiohttp.ClientSession() as session:
        auth = CredentialsAuth(session, creds)
        api = GoogleHealthApi(auth)

        try:
            profile = await api.get_profile()
            print("User Profile details:")
            print(f"  Resource Name: {profile.name}")
            print(f"  Age: {profile.age}")
            if profile.membership_start_date:
                d = profile.membership_start_date
                print(f"  Membership Start Date: {d.year}-{d.month:02d}-{d.day:02d}")
            print(
                f"  Stride Length (Walking): {profile.user_configured_walking_stride_length_mm} mm (auto: {profile.auto_walking_stride_length_mm} mm)"
            )
            print(
                f"  Stride Length (Running): {profile.user_configured_running_stride_length_mm} mm (auto: {profile.auto_running_stride_length_mm} mm)"
            )
        except HealthApiException as err:
            print(f"Failed to fetch profile: {err}")


async def run_settings_get(args) -> None:
    """Retrieve and display user settings."""
    creds = load_credentials()
    if not creds:
        print(
            "ERROR: Not logged in. Please run `python examples/google_health_cli.py login` first."
        )
        sys.exit(1)

    async with aiohttp.ClientSession() as session:
        auth = CredentialsAuth(session, creds)
        api = GoogleHealthApi(auth)

        try:
            settings = await api.get_settings()
            print("User Settings:")
            print(f"  Resource Name: {settings.name}")
            print(
                f"  Timezone: {settings.time_zone} (UTC offset: {settings.utc_offset})"
            )
            print(f"  Distance Unit: {settings.distance_unit}")
            print(f"  Height Unit: {settings.height_unit}")
            print(f"  Weight Unit: {settings.weight_unit}")
            print(f"  Water Unit: {settings.water_unit}")
            print(f"  Temperature Unit: {settings.temperature_unit}")
            print(
                f"  Language Locale: {settings.language_locale} (Food language: {settings.food_language_code})"
            )
        except HealthApiException as err:
            print(f"Failed to fetch settings: {err}")


async def run_devices_list(args) -> None:
    """List paired devices of the user."""
    creds = load_credentials()
    if not creds:
        print(
            "ERROR: Not logged in. Please run `python examples/google_health_cli.py login` first."
        )
        sys.exit(1)

    async with aiohttp.ClientSession() as session:
        auth = CredentialsAuth(session, creds)
        api = GoogleHealthApi(auth)

        try:
            result = await api.paired_devices.list(page_size=args.limit)
            print(f"Paired devices (limit: {args.limit}):")
            for device in result.paired_devices:
                print(f"  - {device.device_version} ({device.device_type})")
                print(f"    Name: {device.name}")
                print(f"    Mac Address: {device.mac_address}")
                print(f"    Battery: {device.battery_level}% ({device.battery_status})")
                print(f"    Last Sync Time: {device.last_sync_time}")
                print(f"    Features: {', '.join(device.features)}")
        except HealthApiException as err:
            print(f"Failed to fetch paired devices: {err}")


def cmd_steps(args) -> None:
    """Handle steps subcommand."""
    asyncio.run(run_steps_list(args))


def cmd_heart_rate(args) -> None:
    """Handle heart rate subcommand."""
    asyncio.run(run_heart_rate_list(args))


def cmd_profile(args) -> None:
    """Handle profile subcommand."""
    asyncio.run(run_profile_get(args))


def cmd_settings(args) -> None:
    """Handle settings subcommand."""
    asyncio.run(run_settings_get(args))


async def run_devices_get(args) -> None:
    """Retrieve and display details of a paired device."""
    creds = load_credentials()
    if not creds:
        print(
            "ERROR: Not logged in. Please run `python examples/google_health_cli.py login` first."
        )
        sys.exit(1)

    async with aiohttp.ClientSession() as session:
        auth = CredentialsAuth(session, creds)
        api = GoogleHealthApi(auth)

        try:
            device = await api.paired_devices.get(device_id=args.device_id)
            print(f"Paired Device Details (ID: {args.device_id}):")
            print(f"  Name: {device.name}")
            print(f"  Version: {device.device_version} ({device.device_type})")
            print(f"  Mac Address: {device.mac_address}")
            print(f"  Battery: {device.battery_level}% ({device.battery_status})")
            print(f"  Last Sync Time: {device.last_sync_time}")
            print(f"  Features: {', '.join(device.features)}")
        except HealthApiException as err:
            print(f"Failed to fetch paired device: {err}")


async def run_identity_get(args) -> None:
    """Retrieve and display identity mapping details."""
    creds = load_credentials()
    if not creds:
        print(
            "ERROR: Not logged in. Please run `python examples/google_health_cli.py login` first."
        )
        sys.exit(1)

    async with aiohttp.ClientSession() as session:
        auth = CredentialsAuth(session, creds)
        api = GoogleHealthApi(auth)

        try:
            identity = await api.get_identity()
            print("User Identity details:")
            print(f"  Name: {identity.name}")
            print(f"  Health User ID: {identity.health_user_id}")
            print(f"  Legacy User ID: {identity.legacy_user_id}")
        except HealthApiException as err:
            print(f"Failed to fetch identity: {err}")


async def run_irn_get(args) -> None:
    """Retrieve and display IRN profile details."""
    creds = load_credentials()
    if not creds:
        print(
            "ERROR: Not logged in. Please run `python examples/google_health_cli.py login` first."
        )
        sys.exit(1)

    async with aiohttp.ClientSession() as session:
        auth = CredentialsAuth(session, creds)
        api = GoogleHealthApi(auth)

        try:
            irn = await api.get_irn_profile()
            print("Irregular Rhythm Notification (IRN) Profile:")
            print(f"  Name: {irn.name}")
            print(f"  Onboarding Status: {irn.onboarding_status}")
            print(f"  Enrollment Status: {irn.enrollment_status}")
            print(f"  Update Time: {irn.update_time}")
        except HealthApiException as err:
            print(f"Failed to fetch IRN profile: {err}")


def cmd_devices(args) -> None:
    """Handle paired devices subcommand."""
    if args.subcommand == "list":
        asyncio.run(run_devices_list(args))
    elif args.subcommand == "get":
        asyncio.run(run_devices_get(args))


def cmd_identity(args) -> None:
    """Handle identity subcommand."""
    asyncio.run(run_identity_get(args))


def cmd_irn(args) -> None:
    """Handle IRN subcommand."""
    asyncio.run(run_irn_get(args))


def main() -> None:
    """Run CLI parser."""
    parser = argparse.ArgumentParser(description="Google Health API CLI tool")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # login command
    subparsers.add_parser("login", help="Log in via browser and save credentials")

    # steps list command
    steps_parser = subparsers.add_parser("steps", help="Manage steps data")
    steps_subparsers = steps_parser.add_subparsers(dest="subcommand", required=True)
    steps_list_parser = steps_subparsers.add_parser("list", help="List steps data")
    steps_list_parser.add_argument(
        "--days", type=int, default=1, help="Number of days of history to fetch"
    )
    steps_list_parser.add_argument(
        "--limit", type=int, default=10, help="Maximum number of records to fetch"
    )
    steps_list_parser.set_defaults(func=cmd_steps)

    # heart-rate list command
    hr_parser = subparsers.add_parser("heart-rate", help="Manage heart rate data")
    hr_subparsers = hr_parser.add_subparsers(dest="subcommand", required=True)
    hr_list_parser = hr_subparsers.add_parser("list", help="List heart rate data")
    hr_list_parser.add_argument(
        "--days", type=int, default=1, help="Number of days of history to fetch"
    )
    hr_list_parser.add_argument(
        "--limit", type=int, default=10, help="Maximum number of records to fetch"
    )
    hr_list_parser.set_defaults(func=cmd_heart_rate)

    # profile get command
    profile_parser = subparsers.add_parser("profile", help="Manage profile data")
    profile_subparsers = profile_parser.add_subparsers(dest="subcommand", required=True)
    profile_get_parser = profile_subparsers.add_parser(
        "get", help="Get profile details"
    )
    profile_get_parser.set_defaults(func=cmd_profile)

    # settings get command
    settings_parser = subparsers.add_parser("settings", help="Manage settings")
    settings_subparsers = settings_parser.add_subparsers(
        dest="subcommand", required=True
    )
    settings_get_parser = settings_subparsers.add_parser(
        "get", help="Get settings details"
    )
    settings_get_parser.set_defaults(func=cmd_settings)

    # devices list command
    devices_parser = subparsers.add_parser("devices", help="Manage paired devices")
    devices_subparsers = devices_parser.add_subparsers(dest="subcommand", required=True)
    devices_list_parser = devices_subparsers.add_parser(
        "list", help="List paired devices"
    )
    devices_list_parser.add_argument(
        "--limit", type=int, default=10, help="Maximum number of devices to fetch"
    )
    devices_list_parser.set_defaults(func=cmd_devices)
    devices_get_parser = devices_subparsers.add_parser(
        "get", help="Get details of a paired device"
    )
    devices_get_parser.add_argument("device_id", type=str, help="The paired device ID")
    devices_get_parser.set_defaults(func=cmd_devices)

    # identity get command
    identity_parser = subparsers.add_parser(
        "identity", help="Manage user identity mapping"
    )
    identity_subparsers = identity_parser.add_subparsers(
        dest="subcommand", required=True
    )
    identity_get_parser = identity_subparsers.add_parser(
        "get", help="Get identity mapping details"
    )
    identity_get_parser.set_defaults(func=cmd_identity)

    # irn get command
    irn_parser = subparsers.add_parser("irn", help="Manage IRN profile")
    irn_subparsers = irn_parser.add_subparsers(dest="subcommand", required=True)
    irn_get_parser = irn_subparsers.add_parser(
        "get", help="Get Irregular Rhythm Notification profile details"
    )
    irn_get_parser.set_defaults(func=cmd_irn)

    args = parser.parse_args()

    if args.command == "login":
        cmd_login(args)
    else:
        args.func(args)


if __name__ == "__main__":
    main()
