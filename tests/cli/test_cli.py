"""Tests for the Google Health CLI."""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from google_health_api.cli.commands import (
    CliHealthSession,
    fields_var,
    serialize_response,
)
from google_health_api.cli.validation import validate_resource_name, validate_safe_path
from google_health_api.client import GoogleHealthSession
from google_health_api.exceptions import HealthApiException
from tests.cli.conftest import run_cli


@pytest.mark.parametrize(
    "name",
    [
        "users/me/profile",
        "users/me/settings",
        "users/me/dataTypes/steps/dataPoints/p123",
        "users/me/dataTypes/weight/dataPoints/w_456-789",
        "projects/my-project/subscribers/sub-123",
        "projects/my-project/subscribers/sub-123/subscriptions/sub_id_456",
        "simple-id",
        "id_with_dash-123",
        "",
    ],
)
def test_validate_resource_name_success(name: str) -> None:
    """Test resource name input validation with valid inputs."""
    # Should not raise any exception
    validate_resource_name(name)


@pytest.mark.parametrize(
    ("name", "match"),
    [
        ("users/me/dataTypes/steps/dataPoints/p123\n", "control characters"),
        ("users/me/dataTypes/steps/dataPoints/p123\x00", "control characters"),
        ("users/me/dataTypes/steps/dataPoints/p123\r", "control characters"),
        ("users/me/dataTypes/steps/dataPoints/p123?", "forbidden characters"),
        ("users/me/dataTypes/steps/dataPoints/p123#", "forbidden characters"),
        ("users/me/dataTypes/steps/dataPoints/p123%", "forbidden characters"),
        ("users/me/dataTypes/steps/dataPoints/../../p123", "path traversal"),
        ("users/me\\dataPoints", "path traversal"),
    ],
)
def test_validate_resource_name_failure(name: str, match: str) -> None:
    """Test resource name input validation with invalid inputs raising ValueError."""
    with pytest.raises(ValueError, match=match):
        validate_resource_name(name)


def test_validate_safe_path(tmp_path: Path) -> None:
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


def test_cli_validation_rejection(
    mock_load_credentials: MagicMock, capsys: pytest.CaptureFixture[str]
) -> None:
    """Test that CLI validation errors are captured and output as JSON errors."""
    mock_load_credentials.return_value = ("env", "fake-token")

    # Pass an invalid device ID containing forbidden character "?"
    with pytest.raises(SystemExit) as exit_info:
        run_cli(["devices", "get", "dev?id"])
    assert exit_info.value.code == 1

    captured = capsys.readouterr()
    err_json = json.loads(captured.out)
    assert "error" in err_json
    assert err_json["error"]["status"] == "INTERNAL"
    assert "forbidden characters" in err_json["error"]["message"]


def test_cli_dry_run_mutations(
    mock_load_credentials: MagicMock, capsys: pytest.CaptureFixture[str]
) -> None:
    """Test dry-run intercepting mutating operations."""
    mock_load_credentials.return_value = ("env", "fake-token")

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
    with pytest.raises(SystemExit) as exit_info:
        run_cli(
            [
                "--dry-run",
                "--json",
                json.dumps(payload),
                "steps",
                "create",
            ]
        )
    assert exit_info.value.code == 0

    captured = capsys.readouterr()
    dry_run_out = json.loads(captured.out)
    assert dry_run_out["dry_run"] is True
    assert dry_run_out["method"] == "POST"
    assert dry_run_out["payload"] == payload


def test_cli_raw_json_input(
    mock_load_credentials: MagicMock,
    mock_setup_client: MagicMock,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test passing raw --json input payload is correctly processed."""
    mock_load_credentials.return_value = ("env", "fake-token")

    # Setup mock API
    mock_api = MagicMock()
    mock_setup_client.return_value = mock_api

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

    run_cli(
        [
            "--json",
            json.dumps(payload),
            "steps",
            "create",
        ]
    )

    captured = capsys.readouterr()
    res_json = json.loads(captured.out)
    assert res_json["name"] == "users/me/dataTypes/steps/dataPoints/point-1"
    assert res_json["steps"]["count"] == 800
    mock_steps_subapi.create.assert_called_once()


def test_cli_new_datapoints(
    mock_load_credentials: MagicMock,
    mock_setup_client: MagicMock,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test that the new datapoint commands are correctly routed in the CLI."""
    mock_load_credentials.return_value = ("env", "fake-token")

    mock_api = MagicMock()
    mock_setup_client.return_value = mock_api

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

    run_cli(
        [
            "sleep",
            "list",
            "--days",
            "5",
        ]
    )

    mock_sleep_subapi.list.assert_called_once()


def test_cli_weight_rollup(
    mock_load_credentials: MagicMock,
    mock_setup_client: MagicMock,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test that the weight rollup command is correctly routed and executed in the CLI."""
    mock_load_credentials.return_value = ("env", "fake-token")

    mock_api = MagicMock()
    mock_setup_client.return_value = mock_api

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

    run_cli(
        [
            "weight",
            "rollup",
            "--start-date",
            "2026-06-22",
            "--end-date",
            "2026-06-23",
        ]
    )

    mock_weight_subapi.daily_rollup.assert_called_once()

    captured = capsys.readouterr()
    res_json = json.loads(captured.out)
    assert "rollupDataPoints" in res_json
    assert len(res_json["rollupDataPoints"]) == 1
    assert res_json["rollupDataPoints"][0]["weight"]["weightGramsAvg"] == 75000.0


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


def test_cli_additional_datatypes(
    mock_load_credentials: MagicMock,
    mock_setup_client: MagicMock,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test remaining data type CLI subcommands routing."""
    mock_load_credentials.return_value = ("env", "fake-token")
    mock_api = MagicMock()
    mock_setup_client.return_value = mock_api

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

        run_cli([cmd_name, "list"])
        subapi.list.assert_called_once()


def test_cli_datatype_crud_and_options(
    mock_load_credentials: MagicMock,
    mock_setup_client: MagicMock,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test datatype get, patch, delete, and rollup edge cases."""
    mock_load_credentials.return_value = ("env", "fake-token")
    mock_api = MagicMock()
    mock_setup_client.return_value = mock_api

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

    run_cli(["steps", "get", "p1"])
    mock_steps_subapi.get.assert_called_once_with(data_point_id="p1")

    # patch
    mock_steps_subapi.patch.return_value = mock_dp
    payload = {"steps": {"count": 200}}
    run_cli(
        [
            "--json",
            json.dumps(payload),
            "steps",
            "patch",
            "p1",
        ]
    )
    mock_steps_subapi.patch.assert_called_once()

    # delete
    mock_steps_subapi.delete.return_value = None
    run_cli(["steps", "delete", "p1"])
    mock_steps_subapi.delete.assert_called_once_with("p1")
    captured = capsys.readouterr()
    assert "Deleted steps point p1" in captured.out

    # rollup unsupported error (sub_api has no daily_rollup method)
    del mock_steps_subapi.daily_rollup
    with pytest.raises(SystemExit):
        run_cli(["steps", "rollup"])
    captured = capsys.readouterr()
    assert "does not support daily rollups" in captured.out

    # Restore daily_rollup method
    mock_steps_subapi.daily_rollup = AsyncMock(return_value=[])

    # rollup without start_date (fetching settings timezone)
    mock_sett = MagicMock()
    mock_sett.time_zone = "America/Los_Angeles"
    mock_api.get_settings = AsyncMock(return_value=mock_sett)
    run_cli(["steps", "rollup", "--days", "2"])
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
    run_cli(
        [
            "--params",
            json.dumps(params),
            "steps",
            "list",
        ]
    )
    assert mock_steps_subapi.list.called


def test_cli_execute_all_pages(
    mock_load_credentials: MagicMock,
    mock_setup_client: MagicMock,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test execute_all_pages streaming output format for --all flag across resource types."""
    mock_load_credentials.return_value = ("env", "fake-token")
    mock_api = MagicMock()
    mock_setup_client.return_value = mock_api

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

    run_cli(["steps", "list", "--all"])
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
    run_cli(["devices", "list", "--all"])
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
    run_cli(["subscribers", "list", "--all"])
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
    run_cli(
        [
            "subscriptions",
            "list",
            "--parent-subscriber",
            "sub1",
            "--all",
        ]
    )
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


def test_cli_exceptions_handling(
    mock_load_credentials: MagicMock,
    mock_setup_client: MagicMock,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test HealthApiException and general Exception handling in async_run_cmd."""
    mock_load_credentials.return_value = ("env", "fake-token")

    # HealthApiException
    mock_setup_client.side_effect = HealthApiException("API Error")
    with pytest.raises(SystemExit):
        run_cli(["userinfo"])
    captured = capsys.readouterr()
    assert "API Error" in captured.out

    # General Exception
    mock_setup_client.side_effect = Exception("Unexpected Boom")
    with pytest.raises(SystemExit):
        run_cli(["userinfo"])
    captured = capsys.readouterr()
    assert "Unexpected error: Unexpected Boom" in captured.out


def test_cli_invalid_json_payloads(
    mock_load_credentials: MagicMock,
    mock_setup_client: MagicMock,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test invalid JSON strings provided to --json or --params."""
    mock_load_credentials.return_value = ("env", "fake-token")
    mock_setup_client.return_value = MagicMock()

    # Invalid --json
    with pytest.raises(SystemExit):
        run_cli(
            [
                "--json",
                "{invalid_json",
                "steps",
                "create",
            ]
        )
    captured = capsys.readouterr()
    assert "Invalid raw JSON payload" in captured.out

    # Invalid --params
    with pytest.raises(SystemExit):
        run_cli(
            [
                "--params",
                "{invalid_json",
                "steps",
                "list",
            ]
        )
    captured = capsys.readouterr()
    assert "Invalid --params JSON payload" in captured.out
