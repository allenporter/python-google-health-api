"""Tests for settings CLI command."""

import json

import aiohttp
import pytest


@pytest.mark.asyncio
async def test_cli_settings_commands(
    run_cli_against_server,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test settings CLI subcommands."""
    settings_data = {"name": "users/me/settings", "timeZone": "UTC"}

    async def get_settings_handler(
        request: aiohttp.web.Request,
    ) -> aiohttp.web.Response:
        return aiohttp.web.json_response(settings_data)

    async def update_settings_handler(
        request: aiohttp.web.Request,
    ) -> aiohttp.web.Response:
        body = await request.json()
        assert body["timeZone"] == "America/New_York"
        assert request.query.get("updateMask") == "timeZone"
        return aiohttp.web.json_response(body)

    # settings get
    await run_cli_against_server(
        ["settings", "get"],
        [("GET", "v4/users/me/settings", get_settings_handler)],
    )
    captured = capsys.readouterr()
    assert json.loads(captured.out)["timeZone"] == "UTC"

    # settings update with json
    payload = {"name": "users/me/settings", "timeZone": "America/New_York"}
    await run_cli_against_server(
        [
            "--json",
            json.dumps(payload),
            "settings",
            "update",
            "--update-mask",
            "timeZone",
        ],
        [("PATCH", "v4/users/me/settings", update_settings_handler)],
    )

    # settings update missing json
    with pytest.raises(SystemExit):
        await run_cli_against_server(["settings", "update"], [])
