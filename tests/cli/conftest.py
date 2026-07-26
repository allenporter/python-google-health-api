"""Shared pytest fixtures for CLI tests."""

import sys
from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest

from google_health_api.cli.main import main


def run_cli(args: list[str]) -> None:
    """Helper to run the CLI with specific arguments."""
    with patch.object(sys, "argv", ["google-health-cli", *args]):
        main()


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
