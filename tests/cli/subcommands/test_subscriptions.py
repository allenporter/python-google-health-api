"""Tests for subscriptions CLI command."""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from tests.cli.conftest import run_cli


def test_cli_subscriptions_commands(
    mock_load_credentials: MagicMock,
    mock_setup_client: MagicMock,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test subscriptions CLI subcommands."""
    mock_load_credentials.return_value = ("env", "fake-token")
    mock_api = MagicMock()
    mock_setup_client.return_value = mock_api

    mock_subscriptions_api = AsyncMock()
    mock_api.subscribers.subscriptions = mock_subscriptions_api

    # subscriptions list
    mock_subscriptions_api.list.return_value = MagicMock(
        spec=["to_dict"], to_dict=lambda: {"subscriptions": []}
    )
    run_cli(
        [
            "subscriptions",
            "list",
            "--parent-subscriber",
            "projects/me/subscribers/sub1",
        ]
    )
    mock_subscriptions_api.list.assert_called_once()

    # subscriptions create with flags
    mock_subscriptions_api.create.return_value = MagicMock(
        spec=["to_dict"], to_dict=lambda: {"name": "sub1/subscriptions/s1"}
    )
    run_cli(
        [
            "subscriptions",
            "create",
            "--parent-subscriber",
            "projects/me/subscribers/sub1",
            "--user",
            "users/me",
            "--data-types",
            "steps",
        ]
    )
    mock_subscriptions_api.create.assert_called_once()

    # subscriptions create with json
    payload = {"user": "users/me", "dataTypes": ["steps"]}
    run_cli(
        [
            "--json",
            json.dumps(payload),
            "subscriptions",
            "create",
            "--parent-subscriber",
            "projects/me/subscribers/sub1",
        ]
    )

    # subscriptions create missing user
    with pytest.raises(SystemExit):
        run_cli(
            [
                "subscriptions",
                "create",
                "--parent-subscriber",
                "projects/me/subscribers/sub1",
            ]
        )

    # subscriptions patch
    mock_subscriptions_api.patch.return_value = MagicMock(
        spec=["to_dict"], to_dict=dict
    )
    sub_patch_payload = {
        "name": "projects/me/subscribers/sub1/subscriptions/s1",
        "user": "users/me",
        "dataTypes": ["steps", "heart-rate"],
    }
    run_cli(
        [
            "--json",
            json.dumps(sub_patch_payload),
            "subscriptions",
            "patch",
            "projects/me/subscribers/sub1/subscriptions/s1",
        ]
    )

    # subscriptions patch missing json
    with pytest.raises(SystemExit):
        run_cli(
            [
                "subscriptions",
                "patch",
                "projects/me/subscribers/sub1/subscriptions/s1",
            ]
        )

    # subscriptions delete
    mock_subscriptions_api.delete.return_value = None
    run_cli(
        [
            "subscriptions",
            "delete",
            "projects/me/subscribers/sub1/subscriptions/s1",
        ]
    )
    captured = capsys.readouterr()
    assert "Deleted subscription" in captured.out
