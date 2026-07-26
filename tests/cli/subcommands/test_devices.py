"""Tests for devices CLI command."""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from tests.cli.conftest import run_cli


def test_cli_devices_commands(
    mock_load_credentials: MagicMock,
    mock_setup_client: MagicMock,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test devices CLI subcommands."""
    mock_load_credentials.return_value = ("env", "fake-token")
    mock_api = MagicMock()
    mock_setup_client.return_value = mock_api

    mock_devices_api = AsyncMock()
    mock_api.paired_devices = mock_devices_api

    # devices list
    mock_dev_res = MagicMock(spec=["to_dict"])
    mock_dev_res.to_dict.return_value = {"pairedDevices": []}
    mock_devices_api.list.return_value = mock_dev_res
    run_cli(["devices", "list"])
    mock_devices_api.list.assert_called_once()
    capsys.readouterr()

    # devices get
    mock_dev = MagicMock(spec=["to_dict"])
    mock_dev.to_dict.return_value = {"id": "dev123"}
    mock_devices_api.get.return_value = mock_dev
    run_cli(["devices", "get", "dev123"])
    captured = capsys.readouterr()
    assert json.loads(captured.out)["id"] == "dev123"
