"""Tests for subscriptions CLI command."""

import json

import aiohttp
import pytest


@pytest.mark.asyncio
async def test_cli_subscriptions_commands(
    run_cli_against_server,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test subscriptions CLI subcommands."""

    async def list_subscriptions_handler(
        request: aiohttp.web.Request,
    ) -> aiohttp.web.Response:
        return aiohttp.web.json_response({"subscriptions": []})

    async def create_subscription_handler(
        request: aiohttp.web.Request,
    ) -> aiohttp.web.Response:
        body = await request.json()
        assert body["user"] == "users/me"
        assert body["dataTypes"] == ["steps"]
        return aiohttp.web.json_response(
            {
                "name": "projects/me/subscribers/sub1/subscriptions/s1",
                "user": "users/me",
                "dataTypes": ["steps"],
            }
        )

    async def patch_subscription_handler(
        request: aiohttp.web.Request,
    ) -> aiohttp.web.Response:
        body = await request.json()
        assert body["dataTypes"] == ["steps", "heart-rate"]
        return aiohttp.web.json_response(body)

    async def delete_subscription_handler(
        request: aiohttp.web.Request,
    ) -> aiohttp.web.Response:
        return aiohttp.web.Response(status=200)

    # subscriptions list
    await run_cli_against_server(
        [
            "subscriptions",
            "list",
            "--parent-subscriber",
            "projects/me/subscribers/sub1",
        ],
        [
            (
                "GET",
                "v4/projects/me/subscribers/sub1/subscriptions",
                list_subscriptions_handler,
            )
        ],
    )

    # subscriptions create with flags
    await run_cli_against_server(
        [
            "subscriptions",
            "create",
            "--parent-subscriber",
            "projects/me/subscribers/sub1",
            "--user",
            "users/me",
            "--data-types",
            "steps",
        ],
        [
            (
                "POST",
                "v4/projects/me/subscribers/sub1/subscriptions",
                create_subscription_handler,
            )
        ],
    )

    # subscriptions create with json
    payload = {"user": "users/me", "dataTypes": ["steps"]}
    await run_cli_against_server(
        [
            "--json",
            json.dumps(payload),
            "subscriptions",
            "create",
            "--parent-subscriber",
            "projects/me/subscribers/sub1",
        ],
        [
            (
                "POST",
                "v4/projects/me/subscribers/sub1/subscriptions",
                create_subscription_handler,
            )
        ],
    )

    # subscriptions create missing user
    with pytest.raises(SystemExit):
        await run_cli_against_server(
            [
                "subscriptions",
                "create",
                "--parent-subscriber",
                "projects/me/subscribers/sub1",
            ],
            [],
        )

    # subscriptions patch
    sub_patch_payload = {
        "name": "projects/me/subscribers/sub1/subscriptions/s1",
        "user": "users/me",
        "dataTypes": ["steps", "heart-rate"],
    }
    await run_cli_against_server(
        [
            "--json",
            json.dumps(sub_patch_payload),
            "subscriptions",
            "patch",
            "projects/me/subscribers/sub1/subscriptions/s1",
        ],
        [
            (
                "PATCH",
                "v4/projects/me/subscribers/sub1/subscriptions/s1",
                patch_subscription_handler,
            )
        ],
    )

    # subscriptions patch missing json
    with pytest.raises(SystemExit):
        await run_cli_against_server(
            [
                "subscriptions",
                "patch",
                "projects/me/subscribers/sub1/subscriptions/s1",
            ],
            [],
        )

    # subscriptions delete
    await run_cli_against_server(
        [
            "subscriptions",
            "delete",
            "projects/me/subscribers/sub1/subscriptions/s1",
        ],
        [
            (
                "DELETE",
                "v4/projects/me/subscribers/sub1/subscriptions/s1",
                delete_subscription_handler,
            )
        ],
    )
    captured = capsys.readouterr()
    assert "Deleted subscription" in captured.out
