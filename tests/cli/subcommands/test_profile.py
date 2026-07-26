"""Tests for profile CLI command."""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from tests.cli.conftest import run_cli


def test_cli_profile_commands(
    mock_load_credentials: MagicMock,
    mock_setup_client: MagicMock,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test profile CLI subcommands."""
    mock_load_credentials.return_value = ("env", "fake-token")
    mock_api = MagicMock()
    mock_setup_client.return_value = mock_api

    # profile get
    mock_prof = MagicMock(spec=["to_dict"])
    mock_prof.to_dict.return_value = {
        "name": "users/me/profile",
        "displayName": "Alice",
    }
    mock_api.get_profile = AsyncMock(return_value=mock_prof)

    run_cli(["profile", "get"])
    captured = capsys.readouterr()
    assert json.loads(captured.out)["displayName"] == "Alice"

    # profile update with json & update-mask & dry-run
    payload = {"name": "users/me/profile", "displayName": "Bob"}
    with pytest.raises(SystemExit) as exit_info:
        run_cli(
            [
                "--dry-run",
                "--json",
                json.dumps(payload),
                "--params",
                json.dumps({"updateMask": "displayName"}),
                "profile",
                "update",
            ]
        )
    assert exit_info.value.code == 0
    captured = capsys.readouterr()
    assert "dry_run" in json.loads(captured.out)

    # profile update execution
    mock_api.update_profile = AsyncMock(return_value=mock_prof)
    run_cli(
        [
            "--json",
            json.dumps(payload),
            "profile",
            "update",
            "--update-mask",
            "displayName",
        ]
    )
    mock_api.update_profile.assert_called_once()

    # profile update missing json
    with pytest.raises(SystemExit):
        run_cli(["profile", "update"])
    captured = capsys.readouterr()
    assert "Please provide raw JSON input" in captured.out
