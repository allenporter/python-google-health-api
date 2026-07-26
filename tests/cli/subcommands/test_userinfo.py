"""Tests for userinfo CLI command."""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from tests.cli.conftest import run_cli


def test_cli_userinfo(
    mock_load_credentials: MagicMock,
    mock_setup_client: MagicMock,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test that the userinfo command is correctly routed and executed in the CLI."""
    mock_load_credentials.return_value = ("env", "fake-token")

    mock_api = MagicMock()
    mock_setup_client.return_value = mock_api

    mock_userinfo = MagicMock(spec=["to_dict"])
    mock_userinfo.to_dict.return_value = {
        "sub": "110248495921238986420",
        "name": "John Doe",
        "email": "johndoe@example.com",
    }
    mock_api.get_user_info = AsyncMock(return_value=mock_userinfo)

    run_cli(["userinfo"])

    mock_api.get_user_info.assert_called_once()
    captured = capsys.readouterr()
    res_json = json.loads(captured.out)
    assert res_json["sub"] == "110248495921238986420"
    assert res_json["name"] == "John Doe"
