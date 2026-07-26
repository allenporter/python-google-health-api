"""CLI authentication and session wrappers."""

import asyncio
import contextvars
import json
import os
from datetime import UTC, datetime
from typing import Any

import aiohttp
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

from google_health_api.auth import AbstractAuth
from google_health_api.client import GoogleHealthSession
from google_health_api.const import HealthApiScope

TOKEN_FILE = "token.json"
CLIENT_SECRET_FILE = "client_secret.json"
SCOPES = [
    HealthApiScope.ACTIVITY_READ,
    HealthApiScope.ACTIVITY_WRITE,
    HealthApiScope.MEASUREMENTS_READ,
    HealthApiScope.MEASUREMENTS_WRITE,
    HealthApiScope.PROFILE_READ,
    HealthApiScope.PROFILE_WRITE,
    HealthApiScope.SETTINGS_READ,
    HealthApiScope.SETTINGS_WRITE,
    HealthApiScope.SLEEP_READ,
    HealthApiScope.SLEEP_WRITE,
    HealthApiScope.NUTRITION_READ,
    HealthApiScope.NUTRITION_WRITE,
    HealthApiScope.LOCATION_READ,
    HealthApiScope.ECG_READ,
    HealthApiScope.IRN_READ,
    HealthApiScope.USERINFO_PROFILE,
    HealthApiScope.USERINFO_EMAIL,
]

fields_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "fields", default=None
)


class CliHealthSession(GoogleHealthSession):
    """Subclass of GoogleHealthSession to support dynamically injecting fields parameter."""

    async def request(
        self,
        method: str,
        url: str,
        headers: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> aiohttp.ClientResponse:
        fields = fields_var.get()
        if fields:
            params = kwargs.setdefault("params", {})
            params["fields"] = fields
        return await super().request(method, url, headers=headers, **kwargs)


class CredentialsAuth(AbstractAuth):
    """Auth wrapper that uses google-auth credentials."""

    def __init__(
        self,
        websession: aiohttp.ClientSession,
        credentials,
        host: str | None = None,
        token_file: str | None = None,
    ) -> None:
        super().__init__(websession, host)
        self._credentials = credentials
        self._token_file = token_file

    async def async_get_access_token(self) -> str:
        if not self._credentials.valid:
            loop = asyncio.get_running_loop()
            req = Request()
            await loop.run_in_executor(None, self._credentials.refresh, req)
            save_credentials(self._credentials, token_file=self._token_file)
        return self._credentials.token


class EnvAuth(AbstractAuth):
    """Auth wrapper that uses environment variable token directly (Agent DX)."""

    def __init__(
        self, websession: aiohttp.ClientSession, token: str, host: str | None = None
    ) -> None:
        super().__init__(websession, host)
        self._token = token

    async def async_get_access_token(self) -> str:
        return self._token


def save_credentials(credentials, token_file: str | None = None) -> None:
    """Save credentials to local token file."""
    path = token_file or os.environ.get("GOOGLE_HEALTH_CLI_TOKEN_FILE") or TOKEN_FILE
    with open(path, "w") as f:
        f.write(credentials.to_json())


def load_credentials_or_env(
    token_file: str | None = None,
    environ: dict[str, str] | None = None,
):
    """Load credentials from environment or token.json."""
    env = environ if environ is not None else os.environ
    token_env = env.get("GOOGLE_HEALTH_CLI_TOKEN")
    if token_env:
        return ("env", token_env)

    path = token_file or env.get("GOOGLE_HEALTH_CLI_TOKEN_FILE") or TOKEN_FILE
    if not os.path.exists(path):
        return None

    with open(path, "r") as f:
        data = json.load(f)

    expiry_str = data.get("expiry")
    expiry = None
    if expiry_str:
        if expiry_str.endswith("Z"):
            expiry = datetime.fromisoformat(expiry_str[:-1])
        else:
            dt = datetime.fromisoformat(expiry_str)
            if dt.tzinfo is not None:
                dt = dt.astimezone(UTC).replace(tzinfo=None)
            expiry = dt

    creds = Credentials(
        token=data.get("token"),
        refresh_token=data.get("refresh_token"),
        token_uri=data.get("token_uri"),
        client_id=data.get("client_id"),
        client_secret=data.get("client_secret"),
        scopes=data.get("scopes") or SCOPES,
        expiry=expiry,
    )
    return ("file", creds)
