"""Tests for login and auth flow CLI commands."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from google_health_api.cli.auth import (
    CredentialsAuth,
    EnvAuth,
    load_credentials_or_env,
)
from google_health_api.cli.subcommands.login import cmd_login
from tests.cli.conftest import run_cli


@pytest.mark.asyncio
async def test_credentials_auth_refresh(tmp_path: Path) -> None:
    """Test CredentialsAuth refreshing expired credentials."""
    token_file = tmp_path / "token.json"

    creds_mock = MagicMock()
    creds_mock.valid = False
    creds_mock.token = "refreshed-token"
    creds_mock.to_json.return_value = '{"token": "refreshed-token"}'

    session_mock = MagicMock()
    auth = CredentialsAuth(session_mock, creds_mock, token_file=str(token_file))

    token = await auth.async_get_access_token()
    assert token == "refreshed-token"
    assert creds_mock.refresh.called
    assert token_file.exists()


@pytest.mark.asyncio
async def test_env_auth() -> None:
    """Test EnvAuth token retrieval."""
    session_mock = MagicMock()
    auth = EnvAuth(session_mock, "env-secret-token")
    token = await auth.async_get_access_token()
    assert token == "env-secret-token"


def test_load_credentials_or_env(tmp_path: Path) -> None:
    """Test loading credentials from env vs token file."""
    # 1. Test env var set
    res = load_credentials_or_env(environ={"GOOGLE_HEALTH_CLI_TOKEN": "env-tok"})
    assert res == ("env", "env-tok")

    # 2. Test no file and no env var
    token_file = tmp_path / "token.json"
    assert load_credentials_or_env(token_file=str(token_file), environ={}) is None

    # 3. Test token file exists with Z expiry
    token_data = {
        "token": "file-tok",
        "refresh_token": "re-tok",
        "expiry": "2026-12-31T23:59:59Z",
    }
    token_file.write_text(json.dumps(token_data))
    res_file = load_credentials_or_env(token_file=str(token_file), environ={})
    assert res_file is not None
    assert res_file[0] == "file"
    assert res_file[1].token == "file-tok"

    # 4. Token file with non-Z iso string with offset
    token_data["expiry"] = "2026-12-31T23:59:59+00:00"
    token_file.write_text(json.dumps(token_data))
    res_file2 = load_credentials_or_env(token_file=str(token_file), environ={})
    assert res_file2 is not None
    assert res_file2[0] == "file"


def test_cmd_login_missing_client_secret(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Test login failure when client secret file is missing."""
    with pytest.raises(SystemExit):
        cmd_login(
            MagicMock(),
            client_secret_file=str(tmp_path / "nonexistent.json"),
        )
    captured = capsys.readouterr()
    assert "not found" in captured.out


def test_cmd_login_not_tty(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Test login failure in non-interactive environment."""
    secret_file = tmp_path / "client_secret.json"
    secret_file.write_text(json.dumps({"web": {}}))

    with pytest.raises(SystemExit):
        cmd_login(
            MagicMock(),
            client_secret_file=str(secret_file),
            is_tty=False,
        )
    captured = capsys.readouterr()
    assert "headless environment" in captured.out


def test_cmd_login_web_flow(
    mock_flow_cls: MagicMock,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test login web OAuth flow."""
    secret_file = tmp_path / "client_secret.json"
    secret_file.write_text(
        json.dumps({"web": {"redirect_uris": ["http://localhost:8080/"]}})
    )
    token_file = tmp_path / "token.json"

    mock_flow = MagicMock()
    mock_flow_cls.from_client_secrets_file.return_value = mock_flow
    mock_flow.authorization_url.return_value = (
        "https://auth.example.com",
        "state",
    )
    mock_creds = MagicMock()
    mock_creds.to_json.return_value = '{"token": "abc"}'
    mock_flow.credentials = mock_creds

    # Empty response -> error
    with pytest.raises(SystemExit):
        cmd_login(
            MagicMock(),
            client_secret_file=str(secret_file),
            token_file=str(token_file),
            is_tty=True,
            input_func=lambda prompt="": "",
        )

    # Valid auth code response
    cmd_login(
        MagicMock(),
        client_secret_file=str(secret_file),
        token_file=str(token_file),
        is_tty=True,
        input_func=lambda prompt="": "code=auth123",
    )
    assert mock_flow.fetch_token.called


def test_cmd_login_installed_app_flow(
    mock_installed_flow_cls: MagicMock,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test login installed app flow."""
    secret_file = tmp_path / "client_secret.json"
    secret_file.write_text(json.dumps({"installed": {}}))
    token_file = tmp_path / "token.json"

    mock_flow = MagicMock()
    mock_installed_flow_cls.from_client_secrets_file.return_value = mock_flow
    mock_creds = MagicMock()
    mock_creds.to_json.return_value = '{"token": "abc"}'
    mock_flow.run_local_server.return_value = mock_creds

    cmd_login(
        MagicMock(),
        client_secret_file=str(secret_file),
        token_file=str(token_file),
        is_tty=True,
    )
    captured = capsys.readouterr()
    assert "Logged in successfully" in captured.out


def test_unauthenticated_cli_setup(capsys: pytest.CaptureFixture[str]) -> None:
    """Test error when setup_client finds no auth token/credentials."""
    with (
        patch.dict(
            "os.environ",
            {
                "GOOGLE_HEALTH_CLI_TOKEN_FILE": "non_existent_token.json",
            },
            clear=True,
        ),
        pytest.raises(SystemExit),
    ):
        run_cli(["userinfo"])
    captured = capsys.readouterr()
    assert "Not logged in" in captured.out
