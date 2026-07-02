"""Tests for the Google Health CLI."""

import json
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from google_health_api.cli.main import main
from google_health_api.cli.validation import validate_resource_name, validate_safe_path


def test_validate_resource_name() -> None:
    """Test resource name input validation rules."""
    # Safe names should pass without exceptions
    validate_resource_name("safe-id-123")
    validate_resource_name("users/me/profile")

    # Reject control characters (ASCII < 32)
    with pytest.raises(ValueError, match="control characters"):
        validate_resource_name("device\x00id")

    with pytest.raises(ValueError, match="control characters"):
        validate_resource_name("device\x1fid")

    # Reject forbidden injection characters
    with pytest.raises(ValueError, match="forbidden characters"):
        validate_resource_name("id?fields=name")

    with pytest.raises(ValueError, match="forbidden characters"):
        validate_resource_name("sub#delete")

    with pytest.raises(ValueError, match="forbidden characters"):
        validate_resource_name("escape%2e")

    # Reject path traversals
    with pytest.raises(ValueError, match="path traversal"):
        validate_resource_name("../parent")

    with pytest.raises(ValueError, match="path traversal"):
        validate_resource_name("sub\\path")


def test_validate_safe_path(tmp_path) -> None:
    """Test local path sandboxing validation rules."""
    import os

    # Sandbox to current directory
    cwd = os.path.abspath(os.getcwd())

    # Safe relative path resolving within cwd
    validate_safe_path("config.json")
    validate_safe_path("./subdir/config.json")

    # Reject traversals outside
    with pytest.raises(ValueError, match="Path traversal"):
        validate_safe_path("../../outside.json")

    # Reject absolute path pointing outside CWD
    outside_dir = os.path.abspath(os.path.join(cwd, "..", "outside_root.json"))
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
    mock_steps_subapi._data_type = MagicMock()
    mock_steps_subapi._data_type.field_name = "steps"

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
    mock_sleep_subapi._data_type = MagicMock()
    mock_sleep_subapi._data_type.field_name = "sleep"

    # Setup mock return value for list sleep
    mock_sleep_res = MagicMock()
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
    mock_weight_subapi._data_type = MagicMock()
    mock_weight_subapi._data_type.field_name = "weight"

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
