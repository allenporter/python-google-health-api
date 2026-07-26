"""Tests for profile CLI command."""

import json

import aiohttp
import pytest


@pytest.mark.asyncio
async def test_cli_profile_commands(
    run_cli_against_server,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test profile CLI subcommands."""
    profile_data = {
        "name": "users/me/profile",
        "age": 30,
    }

    async def get_profile_handler(
        request: aiohttp.web.Request,
    ) -> aiohttp.web.Response:
        return aiohttp.web.json_response(profile_data)

    async def update_profile_handler(
        request: aiohttp.web.Request,
    ) -> aiohttp.web.Response:
        body = await request.json()
        assert body["age"] == 35
        assert request.query.get("updateMask") == "age"
        return aiohttp.web.json_response(body)

    # profile get
    await run_cli_against_server(
        ["profile", "get"],
        [("GET", "v4/users/me/profile", get_profile_handler)],
    )
    captured = capsys.readouterr()
    assert json.loads(captured.out)["age"] == 30

    # profile update with json & update-mask & dry-run
    payload = {"name": "users/me/profile", "age": 35}
    with pytest.raises(SystemExit) as exit_info:
        await run_cli_against_server(
            [
                "--dry-run",
                "--json",
                json.dumps(payload),
                "--params",
                json.dumps({"updateMask": "age"}),
                "profile",
                "update",
            ],
            [],
        )
    assert exit_info.value.code == 0
    captured = capsys.readouterr()
    assert "dry_run" in json.loads(captured.out)

    # profile update execution
    await run_cli_against_server(
        [
            "--json",
            json.dumps(payload),
            "profile",
            "update",
            "--update-mask",
            "age",
        ],
        [("PATCH", "v4/users/me/profile", update_profile_handler)],
    )

    # profile update missing json
    with pytest.raises(SystemExit):
        await run_cli_against_server(["profile", "update"], [])
    captured = capsys.readouterr()
    assert "Please provide raw JSON input" in captured.out
