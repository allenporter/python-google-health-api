"""Tests for devices CLI command."""

import json

import aiohttp
import pytest


@pytest.mark.asyncio
async def test_cli_devices_commands(
    run_cli_against_server,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test devices CLI subcommands."""
    device_data = {
        "name": "projects/me/pairedDevices/dev123",
        "deviceType": "WATCH",
    }

    async def list_devices_handler(
        request: aiohttp.web.Request,
    ) -> aiohttp.web.Response:
        return aiohttp.web.json_response({"pairedDevices": [device_data]})

    async def get_device_handler(
        request: aiohttp.web.Request,
    ) -> aiohttp.web.Response:
        return aiohttp.web.json_response(device_data)

    # test devices list
    await run_cli_against_server(
        ["devices", "list"],
        [("GET", "v4/users/me/pairedDevices", list_devices_handler)],
    )
    captured = capsys.readouterr()
    assert "WATCH" in captured.out

    # test devices get
    await run_cli_against_server(
        ["devices", "get", "dev123"],
        [("GET", "v4/users/me/pairedDevices/dev123", get_device_handler)],
    )
    captured = capsys.readouterr()
    assert json.loads(captured.out)["name"] == "projects/me/pairedDevices/dev123"
