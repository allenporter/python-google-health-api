"""Tests for identity and irn CLI commands."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from tests.cli.conftest import run_cli


def test_cli_identity_and_irn(
    mock_load_credentials: MagicMock,
    mock_setup_client: MagicMock,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test identity and irn CLI subcommands."""
    mock_load_credentials.return_value = ("env", "fake-token")
    mock_api = MagicMock()
    mock_setup_client.return_value = mock_api

    mock_api.get_identity = AsyncMock(
        return_value=MagicMock(spec=["to_dict"], to_dict=lambda: {"subject": "user123"})
    )
    run_cli(["identity", "get"])
    mock_api.get_identity.assert_called_once()

    mock_api.get_irn_profile = AsyncMock(
        return_value=MagicMock(spec=["to_dict"], to_dict=lambda: {"status": "ok"})
    )
    run_cli(["irn", "get"])
    mock_api.get_irn_profile.assert_called_once()
