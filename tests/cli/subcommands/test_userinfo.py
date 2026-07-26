"""Tests for userinfo CLI command."""

import json

import aiohttp
import pytest


@pytest.mark.asyncio
async def test_cli_userinfo(
    run_cli_against_server,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test that the userinfo command is correctly routed and executed in the CLI."""
    userinfo_data = {
        "sub": "110248495921238986420",
        "name": "John Doe",
        "email": "johndoe@example.com",
    }

    async def get_user_info_handler(
        request: aiohttp.web.Request,
    ) -> aiohttp.web.Response:
        return aiohttp.web.json_response(userinfo_data)

    await run_cli_against_server(
        ["userinfo"],
        [("GET", "oauth2/v3/userinfo", get_user_info_handler)],
    )

    captured = capsys.readouterr()
    res_json = json.loads(captured.out)
    assert res_json["sub"] == "110248495921238986420"
    assert res_json["name"] == "John Doe"
