"""Tests for the Google Health CLI."""

import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from google_health_api.cli.commands import (
    CliHealthSession,
    CredentialsAuth,
    EnvAuth,
    cmd_login,
    fields_var,
    load_credentials_or_env,
    serialize_response,
)
from google_health_api.cli.main import main
from google_health_api.cli.validation import validate_resource_name, validate_safe_path
from google_health_api.client import GoogleHealthSession
from google_health_api.exceptions import HealthApiException


@pytest.mark.parametrize(
    "name",
    [
        "safe-id-123",
        "users/me/profile",
    ],
)
def test_validate_resource_name_success(name: str) -> None:
    """Test resource name input validation with valid inputs."""
    validate_resource_name(name)


@pytest.mark.parametrize(
    ("name", "match"),
    [
        ("device\x00id", "control characters"),
        ("device\x1fid", "control characters"),
        ("id?fields=name", "forbidden characters"),
        ("sub#delete", "forbidden characters"),
        ("escape%2e", "forbidden characters"),
        ("../parent", "path traversal"),
        ("sub\\path", "path traversal"),
    ],
)
def test_validate_resource_name_failure(name: str, match: str) -> None:
    """Test resource name input validation with invalid inputs raising ValueError."""
    with pytest.raises(ValueError, match=match):
        validate_resource_name(name)


def test_validate_safe_path(tmp_path) -> None:
    """Test local path sandboxing validation rules."""
    # Sandbox to current directory
    cwd = Path.cwd().resolve()

    # Safe relative path resolving within cwd
    validate_safe_path("config.json")
    validate_safe_path("./subdir/config.json")

    # Reject traversals outside
    with pytest.raises(ValueError, match="Path traversal"):
        validate_safe_path("../../outside.json")

    # Reject absolute path pointing outside CWD
    outside_dir = str((cwd.parent / "outside_root.json").resolve())
    with pytest.raises(ValueError, match="falls outside"):
        validate_safe_path(outside_dir)


@patch("google_health_api.cli.commands.load_credentials_or_env")
def test_cli_schema(mock_load, capsys) -> None:
    """Test schema introspection commands."""
    # Test listing all schemas
    with patch.object(sys, "argv", ["google-health-cli", "schema"]):
        main()
    captured = capsys.readouterr()
    schemas = json.loads(captured.out)
    assert "steps.list" in schemas
    assert "profile.get" in schemas
    assert "userinfo" in schemas

    # Test retrieving a specific command schema
    with patch.object(sys, "argv", ["google-health-cli", "schema", "steps.list"]):
        main()
    captured = capsys.readouterr()
    schema_details = json.loads(captured.out)
    assert schema_details["method"] == "GET"
    assert schema_details["endpoint"] == "v4/users/{user}/dataTypes/steps/dataPoints"


@patch("google_health_api.cli.commands.load_credentials_or_env")
def test_cli_validation_rejection(mock_load, capsys) -> None:
    """Test that CLI validation errors are captured and output as JSON errors."""
    mock_load.return_value = ("env", "fake-token")

    # Pass an invalid device ID containing forbidden character "?"
    with patch.object(sys, "argv", ["google-health-cli", "devices", "get", "dev?id"]):
        with pytest.raises(SystemExit) as exit_info:
            main()
        assert exit_info.value.code == 1

    captured = capsys.readouterr()
    err_json = json.loads(captured.out)
    assert "error" in err_json
    assert err_json["error"]["status"] == "INTERNAL"
    assert "forbidden characters" in err_json["error"]["message"]


@patch("google_health_api.cli.commands.load_credentials_or_env")
def test_cli_dry_run_mutations(mock_load, capsys) -> None:
    """Test dry-run intercepting mutating operations."""
    mock_load.return_value = ("env", "fake-token")

    # Test dry run for steps create
    payload = {
        "steps": {
            "count": 500,
            "interval": {
                "startTime": "2026-06-22T08:00:00Z",
                "endTime": "2026-06-22T08:15:00Z",
            },
        }
    }
    with patch.object(
        sys,
        "argv",
        [
            "google-health-cli",
            "--dry-run",
            "--json",
            json.dumps(payload),
            "steps",
            "create",
        ],
    ):
        with pytest.raises(SystemExit) as exit_info:
            main()
        assert exit_info.value.code == 0

    captured = capsys.readouterr()
    dry_run_out = json.loads(captured.out)
    assert dry_run_out["dry_run"] is True
    assert dry_run_out["method"] == "POST"
    assert dry_run_out["payload"] == payload


@patch("google_health_api.cli.commands.setup_client")
@patch("google_health_api.cli.commands.load_credentials_or_env")
def test_cli_raw_json_input(mock_load, mock_setup, capsys) -> None:
    """Test passing raw --json input payload is correctly processed."""
    mock_load.return_value = ("env", "fake-token")

    # Setup mock API
    mock_api = MagicMock()
    mock_setup.return_value = mock_api

    mock_steps_subapi = AsyncMock()
    mock_api.steps = mock_steps_subapi
    mock_steps_subapi.data_type = MagicMock()
    mock_steps_subapi.data_type.field_name = "steps"

    # Setup mock return value for create
    mock_res = MagicMock()
    mock_res.name = "users/me/dataTypes/steps/dataPoints/point-1"
    mock_res.data_source = None
    mock_res.data.to_dict.return_value = {
        "count": 800,
        "interval": {
            "startTime": "2026-06-22T08:00:00Z",
            "endTime": "2026-06-22T08:15:00Z",
        },
    }
    mock_steps_subapi.create.return_value = mock_res

    payload = {
        "steps": {
            "count": 800,
            "interval": {
                "startTime": "2026-06-22T08:00:00Z",
                "endTime": "2026-06-22T08:15:00Z",
            },
        }
    }

    with patch.object(
        sys,
        "argv",
        [
            "google-health-cli",
            "--json",
            json.dumps(payload),
            "steps",
            "create",
        ],
    ):
        main()

    captured = capsys.readouterr()
    res_json = json.loads(captured.out)
    assert res_json["name"] == "users/me/dataTypes/steps/dataPoints/point-1"
    assert res_json["steps"]["count"] == 800
    mock_steps_subapi.create.assert_called_once()


@patch("google_health_api.cli.commands.setup_client")
@patch("google_health_api.cli.commands.load_credentials_or_env")
def test_cli_new_datapoints(mock_load, mock_setup, capsys) -> None:
    """Test that the new datapoint commands are correctly routed in the CLI."""
    mock_load.return_value = ("env", "fake-token")

    mock_api = MagicMock()
    mock_setup.return_value = mock_api

    # Mock sleep subapi
    mock_sleep_subapi = AsyncMock()
    mock_api.sleep = mock_sleep_subapi
    mock_sleep_subapi.data_type = MagicMock()
    mock_sleep_subapi.data_type.field_name = "sleep"

    # Setup mock return value for list sleep
    mock_sleep_res = MagicMock(spec=["to_dict"])
    mock_sleep_res.to_dict.return_value = {
        "dataPoints": [],
        "nextPageToken": None,
    }
    mock_sleep_subapi.list.return_value = mock_sleep_res

    with patch.object(
        sys,
        "argv",
        [
            "google-health-cli",
            "sleep",
            "list",
            "--days",
            "5",
        ],
    ):
        main()

    mock_sleep_subapi.list.assert_called_once()


@patch("google_health_api.cli.commands.setup_client")
@patch("google_health_api.cli.commands.load_credentials_or_env")
def test_cli_weight_rollup(mock_load, mock_setup, capsys) -> None:
    """Test that the weight rollup command is correctly routed and executed in the CLI."""
    mock_load.return_value = ("env", "fake-token")

    mock_api = MagicMock()
    mock_setup.return_value = mock_api

    mock_weight_subapi = AsyncMock()
    mock_api.weight = mock_weight_subapi
    mock_weight_subapi.data_type = MagicMock()
    mock_weight_subapi.data_type.field_name = "weight"

    # Setup mock return value for weight daily_rollup
    mock_rollup_point = MagicMock()
    mock_rollup_point.civil_start_time = MagicMock()
    mock_rollup_point.civil_start_time.to_dict.return_value = {
        "date": {"year": 2026, "month": 6, "day": 22}
    }
    mock_rollup_point.civil_end_time = MagicMock()
    mock_rollup_point.civil_end_time.to_dict.return_value = {
        "date": {"year": 2026, "month": 6, "day": 23}
    }

    mock_rollup_data = MagicMock()
    mock_rollup_data.to_dict.return_value = {"weightGramsAvg": 75000.0}
    mock_rollup_point.data = mock_rollup_data

    mock_weight_subapi.daily_rollup.return_value = [mock_rollup_point]

    with patch.object(
        sys,
        "argv",
        [
            "google-health-cli",
            "weight",
            "rollup",
            "--start-date",
            "2026-06-22",
            "--end-date",
            "2026-06-23",
        ],
    ):
        main()

    mock_weight_subapi.daily_rollup.assert_called_once()

    captured = capsys.readouterr()
    res_json = json.loads(captured.out)
    assert "rollupDataPoints" in res_json
    assert len(res_json["rollupDataPoints"]) == 1
    assert res_json["rollupDataPoints"][0]["weight"]["weightGramsAvg"] == 75000.0


@patch("google_health_api.cli.commands.setup_client")
@patch("google_health_api.cli.commands.load_credentials_or_env")
def test_cli_userinfo(mock_load, mock_setup, capsys) -> None:
    """Test that the userinfo command is correctly routed and executed in the CLI."""
    mock_load.return_value = ("env", "fake-token")

    mock_api = MagicMock()
    mock_setup.return_value = mock_api

    mock_userinfo = MagicMock(spec=["to_dict"])
    mock_userinfo.to_dict.return_value = {
        "sub": "110248495921238986420",
        "name": "John Doe",
        "email": "johndoe@example.com",
    }
    mock_api.get_user_info = AsyncMock(return_value=mock_userinfo)

    with patch.object(sys, "argv", ["google-health-cli", "userinfo"]):
        main()

    mock_api.get_user_info.assert_called_once()
    captured = capsys.readouterr()
    res_json = json.loads(captured.out)
    assert res_json["sub"] == "110248495921238986420"
    assert res_json["name"] == "John Doe"


# =====================================================================
# Additional Comprehensive CLI Tests
# =====================================================================


@pytest.mark.asyncio
async def test_cli_health_session_fields_injection() -> None:
    """Test dynamic fields parameter injection in CliHealthSession."""

    auth_mock = AsyncMock()
    auth_mock.async_get_access_token = AsyncMock(return_value="fake-token")
    mock_session = AsyncMock()

    mock_resp = MagicMock(status=200)

    cli_session = CliHealthSession(auth_mock, mock_session, "https://example.com")

    # When fields_var is None
    token_none = fields_var.set(None)
    try:
        with patch.object(
            GoogleHealthSession, "request", new_callable=AsyncMock
        ) as mock_super_req:
            mock_super_req.return_value = mock_resp
            await cli_session.request("GET", "https://example.com/test")
            mock_super_req.assert_called_once_with(
                "GET", "https://example.com/test", headers=None
            )
    finally:
        fields_var.reset(token_none)

    # When fields_var is set
    token_val = fields_var.set("count,interval")
    try:
        with patch.object(
            GoogleHealthSession, "request", new_callable=AsyncMock
        ) as mock_super_req:
            mock_super_req.return_value = mock_resp
            await cli_session.request("GET", "https://example.com/test")
            mock_super_req.assert_called_once_with(
                "GET",
                "https://example.com/test",
                headers=None,
                params={"fields": "count,interval"},
            )
    finally:
        fields_var.reset(token_val)


@pytest.mark.asyncio
async def test_credentials_auth_refresh(tmp_path, monkeypatch) -> None:
    """Test CredentialsAuth refreshing expired credentials."""

    token_file = tmp_path / "token.json"
    monkeypatch.setattr("google_health_api.cli.commands.TOKEN_FILE", str(token_file))

    creds_mock = MagicMock()
    creds_mock.valid = False
    creds_mock.token = "refreshed-token"
    creds_mock.to_json.return_value = '{"token": "refreshed-token"}'

    session_mock = MagicMock()
    auth = CredentialsAuth(session_mock, creds_mock)

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


def test_load_credentials_or_env(tmp_path, monkeypatch) -> None:
    """Test loading credentials from env vs token file."""

    # 1. Test env var set
    monkeypatch.setenv("GOOGLE_HEALTH_CLI_TOKEN", "env-tok")
    res = load_credentials_or_env()
    assert res == ("env", "env-tok")

    # 2. Test no file and no env var
    monkeypatch.delenv("GOOGLE_HEALTH_CLI_TOKEN", raising=False)
    token_file = tmp_path / "token.json"
    monkeypatch.setattr("google_health_api.cli.commands.TOKEN_FILE", str(token_file))
    assert load_credentials_or_env() is None

    # 3. Test token file exists with Z expiry
    token_data = {
        "token": "file-tok",
        "refresh_token": "re-tok",
        "expiry": "2026-12-31T23:59:59Z",
    }
    token_file.write_text(json.dumps(token_data))
    res_file = load_credentials_or_env()
    assert res_file[0] == "file"
    assert res_file[1].token == "file-tok"

    # 4. Token file with non-Z iso string with offset
    token_data["expiry"] = "2026-12-31T23:59:59+00:00"
    token_file.write_text(json.dumps(token_data))
    res_file2 = load_credentials_or_env()
    assert res_file2[0] == "file"


def test_cmd_login_missing_client_secret(tmp_path, monkeypatch, capsys) -> None:
    """Test login failure when client secret file is missing."""

    monkeypatch.setattr(
        "google_health_api.cli.commands.CLIENT_SECRET_FILE",
        str(tmp_path / "nonexistent.json"),
    )
    with pytest.raises(SystemExit):
        cmd_login(MagicMock())
    captured = capsys.readouterr()
    assert "not found" in captured.out


def test_cmd_login_not_tty(tmp_path, monkeypatch, capsys) -> None:
    """Test login failure in non-interactive environment."""

    secret_file = tmp_path / "client_secret.json"
    secret_file.write_text(json.dumps({"web": {}}))
    monkeypatch.setattr(
        "google_health_api.cli.commands.CLIENT_SECRET_FILE", str(secret_file)
    )
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)

    with pytest.raises(SystemExit):
        cmd_login(MagicMock())
    captured = capsys.readouterr()
    assert "headless environment" in captured.out


@patch("google_health_api.cli.commands.Flow")
def test_cmd_login_web_flow(mock_flow_cls, tmp_path, monkeypatch, capsys) -> None:
    """Test login web OAuth flow."""

    secret_file = tmp_path / "client_secret.json"
    secret_file.write_text(
        json.dumps({"web": {"redirect_uris": ["http://localhost:8080/"]}})
    )
    monkeypatch.setattr(
        "google_health_api.cli.commands.CLIENT_SECRET_FILE", str(secret_file)
    )
    monkeypatch.setattr(
        "google_health_api.cli.commands.TOKEN_FILE", str(tmp_path / "token.json")
    )
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)

    mock_flow = MagicMock()
    mock_flow_cls.from_client_secrets_file.return_value = mock_flow
    mock_flow.authorization_url.return_value = ("https://auth.example.com", "state")
    mock_creds = MagicMock()
    mock_creds.to_json.return_value = '{"token": "abc"}'
    mock_flow.credentials = mock_creds

    # Empty response -> error
    monkeypatch.setattr("builtins.input", lambda prompt="": "")
    with pytest.raises(SystemExit):
        cmd_login(MagicMock())

    # Valid auth code response
    monkeypatch.setattr("builtins.input", lambda prompt="": "code=auth123")
    cmd_login(MagicMock())
    assert mock_flow.fetch_token.called


@patch("google_health_api.cli.commands.InstalledAppFlow")
def test_cmd_login_installed_app_flow(
    mock_flow_cls, tmp_path, monkeypatch, capsys
) -> None:
    """Test login installed app flow."""

    secret_file = tmp_path / "client_secret.json"
    secret_file.write_text(json.dumps({"installed": {}}))
    monkeypatch.setattr(
        "google_health_api.cli.commands.CLIENT_SECRET_FILE", str(secret_file)
    )
    monkeypatch.setattr(
        "google_health_api.cli.commands.TOKEN_FILE", str(tmp_path / "token.json")
    )
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)

    mock_flow = MagicMock()
    mock_flow_cls.from_client_secrets_file.return_value = mock_flow
    mock_creds = MagicMock()
    mock_creds.to_json.return_value = '{"token": "abc"}'
    mock_flow.run_local_server.return_value = mock_creds

    cmd_login(MagicMock())
    captured = capsys.readouterr()
    assert "Logged in successfully" in captured.out


@patch("google_health_api.cli.commands.setup_client")
@patch("google_health_api.cli.commands.load_credentials_or_env")
def test_cli_profile_commands(mock_load, mock_setup, capsys) -> None:
    """Test profile CLI subcommands."""
    mock_load.return_value = ("env", "fake-token")
    mock_api = MagicMock()
    mock_setup.return_value = mock_api

    # profile get
    mock_prof = MagicMock(spec=["to_dict"])
    mock_prof.to_dict.return_value = {
        "name": "users/me/profile",
        "displayName": "Alice",
    }
    mock_api.get_profile = AsyncMock(return_value=mock_prof)

    with patch.object(sys, "argv", ["google-health-cli", "profile", "get"]):
        main()
    captured = capsys.readouterr()
    assert json.loads(captured.out)["displayName"] == "Alice"

    # profile update with json & update-mask & dry-run
    payload = {"name": "users/me/profile", "displayName": "Bob"}
    with patch.object(
        sys,
        "argv",
        [
            "google-health-cli",
            "--dry-run",
            "--json",
            json.dumps(payload),
            "--params",
            json.dumps({"updateMask": "displayName"}),
            "profile",
            "update",
        ],
    ):
        with pytest.raises(SystemExit) as exit_info:
            main()
        assert exit_info.value.code == 0
    captured = capsys.readouterr()
    assert "dry_run" in json.loads(captured.out)

    # profile update execution
    mock_api.update_profile = AsyncMock(return_value=mock_prof)
    with patch.object(
        sys,
        "argv",
        [
            "google-health-cli",
            "--json",
            json.dumps(payload),
            "profile",
            "update",
            "--update-mask",
            "displayName",
        ],
    ):
        main()
    mock_api.update_profile.assert_called_once()

    # profile update missing json
    with (
        patch.object(sys, "argv", ["google-health-cli", "profile", "update"]),
        pytest.raises(SystemExit),
    ):
        main()
    captured = capsys.readouterr()
    assert "Please provide raw JSON input" in captured.out


@patch("google_health_api.cli.commands.setup_client")
@patch("google_health_api.cli.commands.load_credentials_or_env")
def test_cli_settings_commands(mock_load, mock_setup, capsys) -> None:
    """Test settings CLI subcommands."""
    mock_load.return_value = ("env", "fake-token")
    mock_api = MagicMock()
    mock_setup.return_value = mock_api

    # settings get
    mock_sett = MagicMock(spec=["to_dict"])
    mock_sett.to_dict.return_value = {"name": "users/me/settings", "timeZone": "UTC"}
    mock_api.get_settings = AsyncMock(return_value=mock_sett)

    with patch.object(sys, "argv", ["google-health-cli", "settings", "get"]):
        main()
    captured = capsys.readouterr()
    assert json.loads(captured.out)["timeZone"] == "UTC"

    # settings update with json
    mock_api.update_settings = AsyncMock(return_value=mock_sett)
    payload = {"name": "users/me/settings", "timeZone": "America/New_York"}
    with patch.object(
        sys,
        "argv",
        [
            "google-health-cli",
            "--json",
            json.dumps(payload),
            "settings",
            "update",
            "--update-mask",
            "timeZone",
        ],
    ):
        main()
    mock_api.update_settings.assert_called_once()

    # settings update missing json
    with (
        patch.object(sys, "argv", ["google-health-cli", "settings", "update"]),
        pytest.raises(SystemExit),
    ):
        main()


@patch("google_health_api.cli.commands.setup_client")
@patch("google_health_api.cli.commands.load_credentials_or_env")
def test_cli_devices_commands(mock_load, mock_setup, capsys) -> None:
    """Test devices CLI subcommands."""
    mock_load.return_value = ("env", "fake-token")
    mock_api = MagicMock()
    mock_setup.return_value = mock_api

    mock_devices_api = AsyncMock()
    mock_api.paired_devices = mock_devices_api

    # devices list
    mock_dev_res = MagicMock(spec=["to_dict"])
    mock_dev_res.to_dict.return_value = {"pairedDevices": []}
    mock_devices_api.list.return_value = mock_dev_res
    with patch.object(sys, "argv", ["google-health-cli", "devices", "list"]):
        main()
    mock_devices_api.list.assert_called_once()
    capsys.readouterr()

    # devices get
    mock_dev = MagicMock(spec=["to_dict"])
    mock_dev.to_dict.return_value = {"id": "dev123"}
    mock_devices_api.get.return_value = mock_dev
    with patch.object(sys, "argv", ["google-health-cli", "devices", "get", "dev123"]):
        main()
    captured = capsys.readouterr()
    assert json.loads(captured.out)["id"] == "dev123"


@patch("google_health_api.cli.commands.setup_client")
@patch("google_health_api.cli.commands.load_credentials_or_env")
def test_cli_subscribers_commands(mock_load, mock_setup, capsys) -> None:
    """Test subscribers CLI subcommands."""
    mock_load.return_value = ("env", "fake-token")
    mock_api = MagicMock()
    mock_setup.return_value = mock_api

    mock_sub_api = AsyncMock()
    mock_api.subscribers = mock_sub_api

    # subscribers list
    mock_sub_api.list.return_value = MagicMock(
        spec=["to_dict"], to_dict=lambda: {"subscribers": []}
    )
    with patch.object(sys, "argv", ["google-health-cli", "subscribers", "list"]):
        main()
    mock_sub_api.list.assert_called_once()

    # subscribers create with flags and dry-run
    with patch.object(
        sys,
        "argv",
        [
            "google-health-cli",
            "--dry-run",
            "subscribers",
            "create",
            "--endpoint-uri",
            "https://example.com/webhook",
            "--endpoint-secret",
            "secret123",
        ],
    ):
        with pytest.raises(SystemExit) as exit_info:
            main()
        assert exit_info.value.code == 0

    # subscribers create with json
    payload = {
        "name": "projects/me/subscribers/sub1",
        "endpointUri": "https://example.com/webhook",
        "endpointAuthorization": {"secret": "secret123"},
        "subscriberConfigs": [{"dataType": "steps"}],
    }
    mock_sub_api.create.return_value = MagicMock(
        spec=["to_dict"], to_dict=lambda: {"name": "sub1"}
    )
    with patch.object(
        sys,
        "argv",
        [
            "google-health-cli",
            "--json",
            json.dumps(payload),
            "subscribers",
            "create",
        ],
    ):
        main()
    mock_sub_api.create.assert_called_once()

    # subscribers create missing endpointUri
    with (
        patch.object(sys, "argv", ["google-health-cli", "subscribers", "create"]),
        pytest.raises(SystemExit),
    ):
        main()

    # subscribers patch
    mock_sub_api.patch.return_value = MagicMock(
        spec=["to_dict"], to_dict=lambda: {"name": "sub1"}
    )
    sub_payload = {
        "name": "projects/me/subscribers/sub1",
        "endpointUri": "https://example.com/new",
        "endpointAuthorization": {"secret": "secret123"},
    }
    with patch.object(
        sys,
        "argv",
        [
            "google-health-cli",
            "--json",
            json.dumps(sub_payload),
            "subscribers",
            "patch",
            "projects/me/subscribers/sub1",
        ],
    ):
        main()
    mock_sub_api.patch.assert_called_once()

    # subscribers patch missing json
    with (
        patch.object(
            sys,
            "argv",
            [
                "google-health-cli",
                "subscribers",
                "patch",
                "projects/me/subscribers/sub1",
            ],
        ),
        pytest.raises(SystemExit),
    ):
        main()

    # subscribers delete
    mock_sub_api.delete.return_value = MagicMock(spec=["to_dict"], to_dict=dict)
    with patch.object(
        sys,
        "argv",
        [
            "google-health-cli",
            "subscribers",
            "delete",
            "projects/me/subscribers/sub1",
            "--force",
        ],
    ):
        main()
    mock_sub_api.delete.assert_called_once()


@patch("google_health_api.cli.commands.setup_client")
@patch("google_health_api.cli.commands.load_credentials_or_env")
def test_cli_subscriptions_commands(mock_load, mock_setup, capsys) -> None:
    """Test subscriptions CLI subcommands."""
    mock_load.return_value = ("env", "fake-token")
    mock_api = MagicMock()
    mock_setup.return_value = mock_api

    mock_subscriptions_api = AsyncMock()
    mock_api.subscribers.subscriptions = mock_subscriptions_api

    # subscriptions list
    mock_subscriptions_api.list.return_value = MagicMock(
        spec=["to_dict"], to_dict=lambda: {"subscriptions": []}
    )
    with patch.object(
        sys,
        "argv",
        [
            "google-health-cli",
            "subscriptions",
            "list",
            "--parent-subscriber",
            "projects/me/subscribers/sub1",
        ],
    ):
        main()
    mock_subscriptions_api.list.assert_called_once()

    # subscriptions create with flags
    mock_subscriptions_api.create.return_value = MagicMock(
        spec=["to_dict"], to_dict=lambda: {"name": "sub1/subscriptions/s1"}
    )
    with patch.object(
        sys,
        "argv",
        [
            "google-health-cli",
            "subscriptions",
            "create",
            "--parent-subscriber",
            "projects/me/subscribers/sub1",
            "--user",
            "users/me",
            "--data-types",
            "steps",
        ],
    ):
        main()
    mock_subscriptions_api.create.assert_called_once()

    # subscriptions create with json
    payload = {"user": "users/me", "dataTypes": ["steps"]}
    with patch.object(
        sys,
        "argv",
        [
            "google-health-cli",
            "--json",
            json.dumps(payload),
            "subscriptions",
            "create",
            "--parent-subscriber",
            "projects/me/subscribers/sub1",
        ],
    ):
        main()

    # subscriptions create missing user
    with (
        patch.object(
            sys,
            "argv",
            [
                "google-health-cli",
                "subscriptions",
                "create",
                "--parent-subscriber",
                "projects/me/subscribers/sub1",
            ],
        ),
        pytest.raises(SystemExit),
    ):
        main()

    # subscriptions patch
    mock_subscriptions_api.patch.return_value = MagicMock(
        spec=["to_dict"], to_dict=dict
    )
    sub_patch_payload = {
        "name": "projects/me/subscribers/sub1/subscriptions/s1",
        "user": "users/me",
        "dataTypes": ["steps", "heart-rate"],
    }
    with patch.object(
        sys,
        "argv",
        [
            "google-health-cli",
            "--json",
            json.dumps(sub_patch_payload),
            "subscriptions",
            "patch",
            "projects/me/subscribers/sub1/subscriptions/s1",
        ],
    ):
        main()

    # subscriptions patch missing json
    with (
        patch.object(
            sys,
            "argv",
            [
                "google-health-cli",
                "subscriptions",
                "patch",
                "projects/me/subscribers/sub1/subscriptions/s1",
            ],
        ),
        pytest.raises(SystemExit),
    ):
        main()

    # subscriptions delete
    mock_subscriptions_api.delete.return_value = None
    with patch.object(
        sys,
        "argv",
        [
            "google-health-cli",
            "subscriptions",
            "delete",
            "projects/me/subscribers/sub1/subscriptions/s1",
        ],
    ):
        main()
    captured = capsys.readouterr()
    assert "Deleted subscription" in captured.out


@patch("google_health_api.cli.commands.setup_client")
@patch("google_health_api.cli.commands.load_credentials_or_env")
def test_cli_identity_and_irn(mock_load, mock_setup, capsys) -> None:
    """Test identity and irn CLI subcommands."""
    mock_load.return_value = ("env", "fake-token")
    mock_api = MagicMock()
    mock_setup.return_value = mock_api

    mock_api.get_identity = AsyncMock(
        return_value=MagicMock(spec=["to_dict"], to_dict=lambda: {"subject": "user123"})
    )
    with patch.object(sys, "argv", ["google-health-cli", "identity", "get"]):
        main()
    mock_api.get_identity.assert_called_once()

    mock_api.get_irn_profile = AsyncMock(
        return_value=MagicMock(spec=["to_dict"], to_dict=lambda: {"status": "ok"})
    )
    with patch.object(sys, "argv", ["google-health-cli", "irn", "get"]):
        main()
    mock_api.get_irn_profile.assert_called_once()


@patch("google_health_api.cli.commands.setup_client")
@patch("google_health_api.cli.commands.load_credentials_or_env")
def test_cli_additional_datatypes(mock_load, mock_setup, capsys) -> None:
    """Test remaining data type CLI subcommands routing."""
    mock_load.return_value = ("env", "fake-token")
    mock_api = MagicMock()
    mock_setup.return_value = mock_api

    datatypes = [
        ("hydration_log", "hydration-log"),
        ("nutrition_log", "nutrition-log"),
        ("daily_respiratory_rate", "daily-respiratory-rate"),
        ("respiratory_rate_sleep_summary", "respiratory-rate-sleep-summary"),
        ("active_energy_burned", "active-energy-burned"),
        ("total_calories", "total-calories"),
        ("floors", "floors"),
        ("daily_resting_heart_rate", "daily-resting-heart-rate"),
        ("heart_rate_variability", "heart-rate-variability"),
        ("daily_heart_rate_variability", "daily-heart-rate-variability"),
        ("altitude", "altitude"),
        ("body_fat", "body-fat"),
        ("active_minutes", "active-minutes"),
        ("active_zone_minutes", "active-zone-minutes"),
        ("blood_glucose", "blood-glucose"),
        ("core_body_temperature", "core-body-temperature"),
        ("sedentary_period", "sedentary-period"),
        ("swim_lengths_data", "swim-lengths-data"),
        ("run_vo2_max", "run-vo2-max"),
        ("activity_level", "activity-level"),
        ("time_in_heart_rate_zone", "time-in-heart-rate-zone"),
        ("calories_in_heart_rate_zone", "calories-in-heart-rate-zone"),
        ("electrocardiogram", "electrocardiogram"),
        ("irregular_rhythm_notification", "irregular-rhythm-notification"),
        ("oxygen_saturation", "oxygen-saturation"),
        ("daily_oxygen_saturation", "daily-oxygen-saturation"),
        ("daily_vo2_max", "daily-vo2-max"),
        ("daily_heart_rate_zones", "daily-heart-rate-zones"),
        ("daily_sleep_temperature_derivations", "daily-sleep-temperature-derivations"),
        ("height", "height"),
        ("bmi", "bmi"),
        ("exercise", "exercise"),
        ("distance", "distance"),
        ("basal_energy_burned", "basal-energy-burned"),
        ("vo2_max", "vo2-max"),
    ]

    for attr_name, cmd_name in datatypes:
        subapi = AsyncMock()
        setattr(mock_api, attr_name, subapi)
        subapi.data_type = MagicMock()
        subapi.data_type.field_name = attr_name
        res_mock = MagicMock(
            spec=["data_points", "next_page_token"],
            data_points=[],
            next_page_token=None,
        )
        subapi.list.return_value = res_mock

        with patch.object(sys, "argv", ["google-health-cli", cmd_name, "list"]):
            main()
        subapi.list.assert_called_once()


@patch("google_health_api.cli.commands.setup_client")
@patch("google_health_api.cli.commands.load_credentials_or_env")
def test_cli_datatype_crud_and_options(mock_load, mock_setup, capsys) -> None:
    """Test datatype get, patch, delete, and rollup edge cases."""
    mock_load.return_value = ("env", "fake-token")
    mock_api = MagicMock()
    mock_setup.return_value = mock_api

    mock_steps_subapi = AsyncMock()
    mock_api.steps = mock_steps_subapi
    mock_steps_subapi.data_type = MagicMock()
    mock_steps_subapi.data_type.field_name = "steps"

    # get
    mock_dp = MagicMock()
    mock_dp.name = "p1"
    mock_dp.data_source = None
    mock_dp.data.to_dict.return_value = {"count": 100}
    mock_steps_subapi.get.return_value = mock_dp

    with patch.object(sys, "argv", ["google-health-cli", "steps", "get", "p1"]):
        main()
    mock_steps_subapi.get.assert_called_once_with(data_point_id="p1")

    # patch
    mock_steps_subapi.patch.return_value = mock_dp
    payload = {"steps": {"count": 200}}
    with patch.object(
        sys,
        "argv",
        ["google-health-cli", "--json", json.dumps(payload), "steps", "patch", "p1"],
    ):
        main()
    mock_steps_subapi.patch.assert_called_once()

    # delete
    mock_steps_subapi.delete.return_value = None
    with patch.object(sys, "argv", ["google-health-cli", "steps", "delete", "p1"]):
        main()
    mock_steps_subapi.delete.assert_called_once_with("p1")
    captured = capsys.readouterr()
    assert "Deleted steps point p1" in captured.out

    # rollup unsupported error (sub_api has no daily_rollup method)
    del mock_steps_subapi.daily_rollup
    with (
        patch.object(sys, "argv", ["google-health-cli", "steps", "rollup"]),
        pytest.raises(SystemExit),
    ):
        main()
    captured = capsys.readouterr()
    assert "does not support daily rollups" in captured.out

    # Restore daily_rollup method
    mock_steps_subapi.daily_rollup = AsyncMock(return_value=[])

    # rollup without start_date (fetching settings timezone)
    mock_sett = MagicMock()
    mock_sett.time_zone = "America/Los_Angeles"
    mock_api.get_settings = AsyncMock(return_value=mock_sett)
    with patch.object(
        sys, "argv", ["google-health-cli", "steps", "rollup", "--days", "2"]
    ):
        main()
    mock_steps_subapi.daily_rollup.assert_called_once()

    # list with --params startTime/endTime/pageSize/pageToken
    params = {
        "startTime": "2026-01-01T00:00:00Z",
        "endTime": "2026-01-02T00:00:00Z",
        "pageSize": 5,
        "pageToken": "tok1",
    }
    mock_steps_subapi.list.return_value = MagicMock(
        spec=["data_points", "next_page_token"], data_points=[], next_page_token=None
    )
    with patch.object(
        sys,
        "argv",
        ["google-health-cli", "--params", json.dumps(params), "steps", "list"],
    ):
        main()
    assert mock_steps_subapi.list.called


@patch("google_health_api.cli.commands.setup_client")
@patch("google_health_api.cli.commands.load_credentials_or_env")
def test_cli_execute_all_pages(mock_load, mock_setup, capsys) -> None:
    """Test execute_all_pages streaming output format for --all flag across resource types."""
    mock_load.return_value = ("env", "fake-token")
    mock_api = MagicMock()
    mock_setup.return_value = mock_api

    # 1. dataPoints list --all
    mock_dp = MagicMock()
    mock_dp.name = "p1"
    mock_dp.data_source = None
    mock_dp.data.to_dict.return_value = {"count": 10}
    page1 = MagicMock(spec=["data_points"], data_points=[mock_dp])

    async def async_iter():
        yield page1

    mock_steps_subapi = AsyncMock()
    mock_api.steps = mock_steps_subapi
    mock_steps_subapi.data_type = MagicMock()
    mock_steps_subapi.data_type.field_name = "steps"
    mock_steps_subapi.list.return_value = async_iter()

    with patch.object(sys, "argv", ["google-health-cli", "steps", "list", "--all"]):
        main()
    captured = capsys.readouterr()
    assert '"name": "p1"' in captured.out

    # 2. pairedDevices list --all
    dev1 = MagicMock(spec=["to_dict"], to_dict=lambda: {"id": "d1"})
    page_dev = MagicMock(spec=["paired_devices"])
    page_dev.paired_devices = [dev1]

    async def async_iter_dev():
        yield page_dev

    mock_dev_api = AsyncMock()
    mock_api.paired_devices = mock_dev_api
    mock_dev_api.list.return_value = async_iter_dev()
    with patch.object(sys, "argv", ["google-health-cli", "devices", "list", "--all"]):
        main()
    captured = capsys.readouterr()
    assert '"id": "d1"' in captured.out

    # 3. subscribers list --all
    sub1 = MagicMock(spec=["to_dict"], to_dict=lambda: {"name": "s1"})
    page_sub = MagicMock(spec=["subscribers"])
    page_sub.subscribers = [sub1]

    async def async_iter_sub():
        yield page_sub

    mock_sub_api = AsyncMock()
    mock_api.subscribers = mock_sub_api
    mock_sub_api.list.return_value = async_iter_sub()
    with patch.object(
        sys, "argv", ["google-health-cli", "subscribers", "list", "--all"]
    ):
        main()
    captured = capsys.readouterr()
    assert '"name": "s1"' in captured.out

    # 4. subscriptions list --all
    subscription1 = MagicMock(
        spec=["to_dict"], to_dict=lambda: {"name": "sub1/subscriptions/s1"}
    )
    page_subscription = MagicMock(spec=["subscriptions"])
    page_subscription.subscriptions = [subscription1]

    async def async_iter_subscription():
        yield page_subscription

    mock_subscriptions_api = AsyncMock()
    mock_api.subscribers.subscriptions = mock_subscriptions_api
    mock_subscriptions_api.list.return_value = async_iter_subscription()
    with patch.object(
        sys,
        "argv",
        [
            "google-health-cli",
            "subscriptions",
            "list",
            "--parent-subscriber",
            "sub1",
            "--all",
        ],
    ):
        main()
    captured = capsys.readouterr()
    assert '"name": "sub1/subscriptions/s1"' in captured.out


def test_serialize_response_reconciled_datapoints() -> None:
    """Test serialize_response for reconciled data points and generic objects."""

    dp = MagicMock()
    dp.name = "p1"
    dp.data_source = None
    dp.data.to_dict.return_value = {"val": 1}

    rdp = MagicMock()
    rdp.data_point = dp

    res = MagicMock(spec=["reconciled_data_points", "next_page_token"])
    res.reconciled_data_points = [rdp]
    res.next_page_token = "tok"

    output = serialize_response(res, "test_field")
    assert output["reconciledDataPoints"][0]["dataPoint"]["name"] == "p1"
    assert output["nextPageToken"] == "tok"

    # Fallback response
    assert serialize_response("plain string") == "plain string"


@patch("google_health_api.cli.commands.setup_client")
@patch("google_health_api.cli.commands.load_credentials_or_env")
def test_cli_exceptions_handling(mock_load, mock_setup, capsys) -> None:
    """Test HealthApiException and general Exception handling in async_run_cmd."""

    mock_load.return_value = ("env", "fake-token")

    # HealthApiException
    mock_setup.side_effect = HealthApiException("API Error")
    with (
        patch.object(sys, "argv", ["google-health-cli", "userinfo"]),
        pytest.raises(SystemExit),
    ):
        main()
    captured = capsys.readouterr()
    assert "API Error" in captured.out

    # General Exception
    mock_setup.side_effect = Exception("Unexpected Boom")
    with (
        patch.object(sys, "argv", ["google-health-cli", "userinfo"]),
        pytest.raises(SystemExit),
    ):
        main()
    captured = capsys.readouterr()
    assert "Unexpected error: Unexpected Boom" in captured.out


@patch("google_health_api.cli.commands.setup_client")
@patch("google_health_api.cli.commands.load_credentials_or_env")
def test_cli_invalid_json_payloads(mock_load, mock_setup, capsys) -> None:
    """Test invalid JSON strings provided to --json or --params."""
    mock_load.return_value = ("env", "fake-token")
    mock_setup.return_value = MagicMock()

    # Invalid --json
    with (
        patch.object(
            sys,
            "argv",
            ["google-health-cli", "--json", "{invalid_json", "steps", "create"],
        ),
        pytest.raises(SystemExit),
    ):
        main()
    captured = capsys.readouterr()
    assert "Invalid raw JSON payload" in captured.out

    # Invalid --params
    with (
        patch.object(
            sys,
            "argv",
            ["google-health-cli", "--params", "{invalid_json", "steps", "list"],
        ),
        pytest.raises(SystemExit),
    ):
        main()
    captured = capsys.readouterr()
    assert "Invalid --params JSON payload" in captured.out


def test_unauthenticated_cli_setup(monkeypatch, capsys) -> None:
    """Test error when setup_client finds no auth token/credentials."""
    monkeypatch.delenv("GOOGLE_HEALTH_CLI_TOKEN", raising=False)
    monkeypatch.setattr(
        "google_health_api.cli.commands.TOKEN_FILE", "non_existent_token.json"
    )

    with (
        patch.object(sys, "argv", ["google-health-cli", "userinfo"]),
        pytest.raises(SystemExit),
    ):
        main()
    captured = capsys.readouterr()
    assert "Not logged in" in captured.out
