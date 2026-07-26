"""Tests for subscribers CLI command."""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from tests.cli.conftest import run_cli


def test_cli_subscribers_commands(
    mock_load_credentials: MagicMock,
    mock_setup_client: MagicMock,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test subscribers CLI subcommands."""
    mock_load_credentials.return_value = ("env", "fake-token")
    mock_api = MagicMock()
    mock_setup_client.return_value = mock_api

    mock_sub_api = AsyncMock()
    mock_api.subscribers = mock_sub_api

    # subscribers list
    mock_sub_api.list.return_value = MagicMock(
        spec=["to_dict"], to_dict=lambda: {"subscribers": []}
    )
    run_cli(["subscribers", "list"])
    mock_sub_api.list.assert_called_once()

    # subscribers create with flags and dry-run
    with pytest.raises(SystemExit) as exit_info:
        run_cli(
            [
                "--dry-run",
                "subscribers",
                "create",
                "--endpoint-uri",
                "https://example.com/webhook",
                "--endpoint-secret",
                "secret123",
            ]
        )
    assert exit_info.value.code == 0

    # subscribers create with json
    payload = {
        "name": "projects/me/subscribers/sub1",
        "endpointUri": "https://example.com/webhook",
        "endpointAuthorization": {"secret": "secret123"},
        "subscriberConfigs": [{"dataType": "steps"}],
    }
    mock_sub_api.create.return_value = MagicMock(
        spec=["to_dict"], to_dict=lambda: {"name": "sub1"}
    )
    run_cli(
        [
            "--json",
            json.dumps(payload),
            "subscribers",
            "create",
        ]
    )
    mock_sub_api.create.assert_called_once()

    # subscribers create missing endpointUri
    with pytest.raises(SystemExit):
        run_cli(["subscribers", "create"])

    # subscribers patch
    mock_sub_api.patch.return_value = MagicMock(
        spec=["to_dict"], to_dict=lambda: {"name": "sub1"}
    )
    sub_payload = {
        "name": "projects/me/subscribers/sub1",
        "endpointUri": "https://example.com/new",
        "endpointAuthorization": {"secret": "secret123"},
    }
    run_cli(
        [
            "--json",
            json.dumps(sub_payload),
            "subscribers",
            "patch",
            "projects/me/subscribers/sub1",
        ]
    )
    mock_sub_api.patch.assert_called_once()

    # subscribers patch missing json
    with pytest.raises(SystemExit):
        run_cli(
            [
                "subscribers",
                "patch",
                "projects/me/subscribers/sub1",
            ]
        )

    # subscribers delete
    mock_sub_api.delete.return_value = MagicMock(spec=["to_dict"], to_dict=dict)
    run_cli(
        [
            "subscribers",
            "delete",
            "projects/me/subscribers/sub1",
            "--force",
        ]
    )
    mock_sub_api.delete.assert_called_once()
