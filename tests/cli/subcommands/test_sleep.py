"""Tests for sleep CLI subcommand."""

import json

import aiohttp
import pytest


@pytest.mark.asyncio
async def test_cli_sleep_commands(
    run_cli_against_server,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test sleep CLI list, get, create, patch, and delete subcommands against mock server."""
    sleep_point_data = {
        "name": "users/me/dataTypes/sleep/dataPoints/sleep-123",
        "sleep": {
            "interval": {
                "startTime": "2026-08-01T22:00:00Z",
                "endTime": "2026-08-02T06:00:00Z",
            },
            "summary": {
                "minutesAsleep": 480,
                "minutesAwake": 30,
            },
        },
    }

    async def list_sleep_handler(
        request: aiohttp.web.Request,
    ) -> aiohttp.web.Response:
        assert "sleep.interval.start_time" in request.query.get("filter", "")
        return aiohttp.web.json_response(
            {
                "dataPoints": [sleep_point_data],
                "nextPageToken": None,
            }
        )

    async def get_sleep_handler(
        request: aiohttp.web.Request,
    ) -> aiohttp.web.Response:
        return aiohttp.web.json_response(sleep_point_data)

    async def create_sleep_handler(
        request: aiohttp.web.Request,
    ) -> aiohttp.web.Response:
        body = await request.json()
        assert body["sleep"]["summary"]["minutesAsleep"] == 480
        return aiohttp.web.json_response(sleep_point_data)

    async def patch_sleep_handler(
        request: aiohttp.web.Request,
    ) -> aiohttp.web.Response:
        body = await request.json()
        assert body["sleep"]["summary"]["minutesAsleep"] == 500
        patched = {
            "name": "users/me/dataTypes/sleep/dataPoints/sleep-123",
            "sleep": {
                "interval": {
                    "startTime": "2026-08-01T22:00:00Z",
                    "endTime": "2026-08-02T06:00:00Z",
                },
                "summary": {
                    "minutesAsleep": 500,
                    "minutesAwake": 30,
                },
            },
        }
        return aiohttp.web.json_response(patched)

    async def delete_sleep_handler(
        request: aiohttp.web.Request,
    ) -> aiohttp.web.Response:
        return aiohttp.web.json_response({})

    # 1. sleep list
    await run_cli_against_server(
        ["sleep", "list", "--days", "7"],
        [("GET", "v4/users/me/dataTypes/sleep/dataPoints", list_sleep_handler)],
    )
    captured = capsys.readouterr()
    res = json.loads(captured.out)
    assert len(res["dataPoints"]) == 1
    assert (
        res["dataPoints"][0]["name"] == "users/me/dataTypes/sleep/dataPoints/sleep-123"
    )
    assert res["dataPoints"][0]["sleep"]["summary"]["minutesAsleep"] == 480

    # 2. sleep get
    await run_cli_against_server(
        ["sleep", "get", "sleep-123"],
        [
            (
                "GET",
                "v4/users/me/dataTypes/sleep/dataPoints/sleep-123",
                get_sleep_handler,
            )
        ],
    )
    captured = capsys.readouterr()
    res = json.loads(captured.out)
    assert res["name"] == "users/me/dataTypes/sleep/dataPoints/sleep-123"

    # 3. sleep create (with dry-run)
    payload_create = {
        "sleep": {
            "interval": {
                "startTime": "2026-08-01T22:00:00Z",
                "endTime": "2026-08-02T06:00:00Z",
            },
            "summary": {
                "minutesAsleep": 480,
            },
        }
    }
    with pytest.raises(SystemExit) as exit_info:
        await run_cli_against_server(
            ["--dry-run", "--json", json.dumps(payload_create), "sleep", "create"],
            [],
        )
    assert exit_info.value.code == 0
    captured = capsys.readouterr()
    assert json.loads(captured.out)["dry_run"] is True

    # 4. sleep create (actual execution)
    await run_cli_against_server(
        ["--json", json.dumps(payload_create), "sleep", "create"],
        [("POST", "v4/users/me/dataTypes/sleep/dataPoints", create_sleep_handler)],
    )
    captured = capsys.readouterr()
    res = json.loads(captured.out)
    assert res["sleep"]["summary"]["minutesAsleep"] == 480

    # 5. sleep patch
    payload_patch = {
        "sleep": {
            "interval": {
                "startTime": "2026-08-01T22:00:00Z",
                "endTime": "2026-08-02T06:00:00Z",
            },
            "summary": {
                "minutesAsleep": 500,
            },
        }
    }
    await run_cli_against_server(
        ["--json", json.dumps(payload_patch), "sleep", "patch", "sleep-123"],
        [
            (
                "PATCH",
                "v4/users/me/dataTypes/sleep/dataPoints/sleep-123",
                patch_sleep_handler,
            )
        ],
    )
    captured = capsys.readouterr()
    res = json.loads(captured.out)
    assert res["sleep"]["summary"]["minutesAsleep"] == 500

    # 6. sleep delete
    await run_cli_against_server(
        ["sleep", "delete", "sleep-123"],
        [
            (
                "POST",
                "v4/users/me/dataTypes/sleep/dataPoints:batchDelete",
                delete_sleep_handler,
            )
        ],
    )
    captured = capsys.readouterr()
    assert "Deleted sleep point sleep-123" in captured.out
