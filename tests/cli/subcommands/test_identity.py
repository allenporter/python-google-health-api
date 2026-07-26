"""Tests for identity and irn CLI commands."""

import json

import aiohttp
import pytest


@pytest.mark.asyncio
async def test_cli_identity_and_irn(
    run_cli_against_server,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test identity and irn CLI subcommands."""

    async def get_identity_handler(
        request: aiohttp.web.Request,
    ) -> aiohttp.web.Response:
        return aiohttp.web.json_response(
            {"name": "users/me/identity", "healthUserId": "user123"}
        )

    async def get_irn_handler(
        request: aiohttp.web.Request,
    ) -> aiohttp.web.Response:
        return aiohttp.web.json_response(
            {"name": "users/me/irnProfile", "onboardingStatus": True}
        )

    # test identity get
    await run_cli_against_server(
        ["identity", "get"],
        [("GET", "v4/users/me/identity", get_identity_handler)],
    )
    captured = capsys.readouterr()
    assert json.loads(captured.out)["healthUserId"] == "user123"

    # test irn get
    await run_cli_against_server(
        ["irn", "get"],
        [("GET", "v4/users/me/irnProfile", get_irn_handler)],
    )
    captured = capsys.readouterr()
    assert json.loads(captured.out)["onboardingStatus"] is True
