"""Tests for subscribers CLI command."""

import json

import aiohttp
import pytest


@pytest.mark.asyncio
async def test_cli_subscribers_commands(
    run_cli_against_server,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test subscribers CLI subcommands."""

    async def list_subscribers_handler(
        request: aiohttp.web.Request,
    ) -> aiohttp.web.Response:
        return aiohttp.web.json_response({"subscribers": []})

    async def create_subscriber_handler(
        request: aiohttp.web.Request,
    ) -> aiohttp.web.Response:
        body = await request.json()
        assert body["endpointUri"] == "https://example.com/webhook"
        assert body["endpointAuthorization"]["secret"] == "secret123"
        return aiohttp.web.json_response(
            {
                "name": "projects/me/operations/op1",
                "done": True,
                "response": {"name": "sub1"},
            }
        )

    async def patch_subscriber_handler(
        request: aiohttp.web.Request,
    ) -> aiohttp.web.Response:
        body = await request.json()
        assert body["endpointUri"] == "https://example.com/new"
        return aiohttp.web.json_response(
            {
                "name": "projects/me/operations/op2",
                "done": True,
                "response": {"name": "sub1"},
            }
        )

    async def delete_subscriber_handler(
        request: aiohttp.web.Request,
    ) -> aiohttp.web.Response:
        assert request.query.get("force") == "true"
        return aiohttp.web.json_response(
            {
                "name": "projects/me/operations/op3",
                "done": True,
            }
        )

    # subscribers list
    await run_cli_against_server(
        ["subscribers", "list"],
        [("GET", "v4/projects/me/subscribers", list_subscribers_handler)],
    )

    # subscribers create with flags and dry-run
    with pytest.raises(SystemExit) as exit_info:
        await run_cli_against_server(
            [
                "--dry-run",
                "subscribers",
                "create",
                "--endpoint-uri",
                "https://example.com/webhook",
                "--endpoint-secret",
                "secret123",
            ],
            [],
        )
    assert exit_info.value.code == 0

    # subscribers create with json
    payload = {
        "name": "projects/me/subscribers/sub1",
        "endpointUri": "https://example.com/webhook",
        "endpointAuthorization": {"secret": "secret123"},
        "subscriberConfigs": [{"dataType": "steps"}],
    }
    await run_cli_against_server(
        [
            "--json",
            json.dumps(payload),
            "subscribers",
            "create",
        ],
        [("POST", "v4/projects/me/subscribers", create_subscriber_handler)],
    )

    # subscribers create missing endpointUri
    with pytest.raises(SystemExit):
        await run_cli_against_server(["subscribers", "create"], [])

    # subscribers patch
    sub_payload = {
        "name": "projects/me/subscribers/sub1",
        "endpointUri": "https://example.com/new",
        "endpointAuthorization": {"secret": "secret123"},
    }
    await run_cli_against_server(
        [
            "--json",
            json.dumps(sub_payload),
            "subscribers",
            "patch",
            "projects/me/subscribers/sub1",
        ],
        [("PATCH", "v4/projects/me/subscribers/sub1", patch_subscriber_handler)],
    )

    # subscribers patch missing json
    with pytest.raises(SystemExit):
        await run_cli_against_server(
            [
                "subscribers",
                "patch",
                "projects/me/subscribers/sub1",
            ],
            [],
        )

    # subscribers delete
    await run_cli_against_server(
        [
            "subscribers",
            "delete",
            "projects/me/subscribers/sub1",
            "--force",
        ],
        [("DELETE", "v4/projects/me/subscribers/sub1", delete_subscriber_handler)],
    )
