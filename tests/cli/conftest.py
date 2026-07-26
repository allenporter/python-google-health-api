"""Shared pytest fixtures for CLI tests."""

import os
import sys
from collections.abc import Awaitable, Callable, Generator
from typing import Any
from unittest.mock import MagicMock, patch

import aiohttp
import pytest

from google_health_api.cli.commands import async_run_cmd
from google_health_api.cli.main import build_parser, main
from google_health_api.client import GoogleHealthSession
from tests.conftest import PATH_PREFIX, AuthCallback


def run_cli(args: list[str]) -> None:
    """Helper to run the CLI with specific arguments."""
    with patch.object(sys, "argv", ["google-health-cli", *args]):
        main()


async def async_run_cli(args: list[str]) -> None:
    """Helper to run the CLI asynchronously within a running loop."""
    parser = build_parser()
    parsed_args = parser.parse_args(args)
    await async_run_cmd(parsed_args)


@pytest.fixture
def mock_load_credentials() -> Generator[MagicMock]:
    """Fixture to mock load_credentials_or_env."""
    with patch("google_health_api.cli.commands.load_credentials_or_env") as mock:
        yield mock


@pytest.fixture
def mock_setup_client() -> Generator[MagicMock]:
    """Fixture to mock setup_client."""
    with patch("google_health_api.cli.commands.setup_client") as mock:
        yield mock


@pytest.fixture
def mock_flow_cls() -> Generator[MagicMock]:
    """Fixture to mock Flow in login subcommand."""
    with patch("google_health_api.cli.subcommands.login.Flow") as mock:
        yield mock


@pytest.fixture
def mock_installed_flow_cls() -> Generator[MagicMock]:
    """Fixture to mock InstalledAppFlow in login subcommand."""
    with patch("google_health_api.cli.subcommands.login.InstalledAppFlow") as mock:
        yield mock


@pytest.fixture
def run_cli_against_server(
    auth_cb: AuthCallback,
) -> Callable[[list[str], list[tuple[str, str, Any]]], Awaitable[None]]:
    """Fixture to run the CLI against a mock server with register endpoints."""

    async def run(
        args: list[str],
        handlers: list[
            tuple[
                str,
                str,
                Callable[[aiohttp.web.Request], Awaitable[aiohttp.web.Response]],
            ]
        ],
    ) -> None:
        auth = await auth_cb(handlers)
        server_url = str(auth._websession.make_url(PATH_PREFIX))

        # Intercept external calls to googleapis.com and redirect to test server
        original_request = GoogleHealthSession.request

        async def mock_request(
            self: GoogleHealthSession,
            method: str,
            url: str,
            *args: Any,
            **kwargs: Any,
        ) -> Any:
            if url.startswith("https://www.googleapis.com/"):
                relative_path = url.replace("https://www.googleapis.com/", "")
                url = f"{server_url}/{relative_path}"
            return await original_request(self, method, url, *args, **kwargs)

        # Direct setup_client to the mock server and stub credentials
        with (
            patch.dict(os.environ, {"GOOGLE_HEALTH_API_URL": server_url}),
            patch(
                "google_health_api.cli.commands.load_credentials_or_env",
                return_value=("env", "fake-token"),
            ),
            patch.object(GoogleHealthSession, "request", mock_request),
        ):
            await async_run_cli(args)

    return run
