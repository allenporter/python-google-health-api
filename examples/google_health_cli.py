"""Command-line interface example for the Google Health API.

Supports logging in via browser, listing steps, and listing heart rate.
"""

import argparse
import asyncio
import os
import sys
from datetime import datetime, timezone, timedelta
import aiohttp

from google_health_api.api import GoogleHealthApi
from google_health_api.auth import AbstractAuth
from google_health_api.exceptions import HealthApiException

TOKEN_FILE = "token.json"
CLIENT_SECRET_FILE = "client_secret.json"
SCOPES = [
    "https://www.googleapis.com/auth/health.steps.read",
    "https://www.googleapis.com/auth/health.heart-rate.read",
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
            import asyncio
            from google.auth.transport.requests import Request

            loop = asyncio.get_running_loop()
            req = Request()
            await loop.run_in_executor(None, self._credentials.refresh, req)
            save_credentials(self._credentials)
        return self._credentials.token


def load_credentials():
    """Load credentials from local token file."""
    if not os.path.exists(TOKEN_FILE):
        return None
    from google.oauth2.credentials import Credentials
    return Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)


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
        print("2. Create an OAuth 2.0 Client ID with application type 'Desktop application'.")
        print("3. Download the JSON credentials file, rename it to 'client_secret.json',")
        print("   and place it in the root folder of this project.")
        sys.exit(1)

    from google_auth_oauthlib.flow import InstalledAppFlow
    
    print("Initializing InstalledAppFlow...")
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
        print("ERROR: Not logged in. Please run `python examples/google_health_cli.py login` first.")
        sys.exit(1)

    async with aiohttp.ClientSession() as session:
        auth = CredentialsAuth(session, creds)
        api = GoogleHealthApi(auth)

        end_time = datetime.now(timezone.utc)
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
                print(f"  - {point.data.count} steps ({point.data.start_time} to {point.data.end_time})")
        except HealthApiException as err:
            print(f"Failed to fetch steps: {err}")


async def run_heart_rate_list(args) -> None:
    """List heart rate from the API."""
    creds = load_credentials()
    if not creds:
        print("ERROR: Not logged in. Please run `python examples/google_health_cli.py login` first.")
        sys.exit(1)

    async with aiohttp.ClientSession() as session:
        auth = CredentialsAuth(session, creds)
        api = GoogleHealthApi(auth)

        end_time = datetime.now(timezone.utc)
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
                print(f"  - {point.data.bpm} BPM ({point.data.start_time} to {point.data.end_time})")
        except HealthApiException as err:
            print(f"Failed to fetch heart rate: {err}")


def cmd_steps(args) -> None:
    """Handle steps subcommand."""
    asyncio.run(run_steps_list(args))


def cmd_heart_rate(args) -> None:
    """Handle heart rate subcommand."""
    asyncio.run(run_heart_rate_list(args))


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
    steps_list_parser.add_argument("--days", type=int, default=1, help="Number of days of history to fetch")
    steps_list_parser.add_argument("--limit", type=int, default=10, help="Maximum number of records to fetch")
    steps_list_parser.set_defaults(func=cmd_steps)

    # heart-rate list command
    hr_parser = subparsers.add_parser("heart-rate", help="Manage heart rate data")
    hr_subparsers = hr_parser.add_subparsers(dest="subcommand", required=True)
    hr_list_parser = hr_subparsers.add_parser("list", help="List heart rate data")
    hr_list_parser.add_argument("--days", type=int, default=1, help="Number of days of history to fetch")
    hr_list_parser.add_argument("--limit", type=int, default=10, help="Maximum number of records to fetch")
    hr_list_parser.set_defaults(func=cmd_heart_rate)

    args = parser.parse_args()

    if args.command == "login":
        cmd_login(args)
    else:
        args.func(args)


if __name__ == "__main__":
    main()
