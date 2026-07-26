"""Tests for settings CLI command."""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from tests.cli.conftest import run_cli


def test_cli_settings_commands(
    mock_load_credentials: MagicMock,
    mock_setup_client: MagicMock,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test settings CLI subcommands."""
    mock_load_credentials.return_value = ("env", "fake-token")
    mock_api = MagicMock()
    mock_setup_client.return_value = mock_api

    # settings get
    mock_sett = MagicMock(spec=["to_dict"])
    mock_sett.to_dict.return_value = {"name": "users/me/settings", "timeZone": "UTC"}
    mock_api.get_settings = AsyncMock(return_value=mock_sett)

    run_cli(["settings", "get"])
    captured = capsys.readouterr()
    assert json.loads(captured.out)["timeZone"] == "UTC"

    # settings update with json
    mock_api.update_settings = AsyncMock(return_value=mock_sett)
    payload = {"name": "users/me/settings", "timeZone": "America/New_York"}
    run_cli(
        [
            "--json",
            json.dumps(payload),
            "settings",
            "update",
            "--update-mask",
            "timeZone",
        ]
    )
    mock_api.update_settings.assert_called_once()

    # settings update missing json
    with pytest.raises(SystemExit):
        run_cli(["settings", "update"])
