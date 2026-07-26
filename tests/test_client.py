"""Tests for google_health_api/client.py."""

from unittest.mock import AsyncMock, MagicMock

import aiohttp
from aiohttp import ClientError, ClientResponseError
from http import HTTPStatus
import pytest

from google_health_api.auth import AbstractAuth
from google_health_api.client import GoogleHealthSession
from google_health_api.exceptions import (
    HealthApiException,
    HealthApiForbiddenException,
    HealthAuthException,
)


class MockAuth(AbstractAuth):
    """Mock auth class for testing."""

    async def async_get_access_token(self) -> str:
        """Return a test access token."""
        return "test-token"


@pytest.fixture
def mock_auth() -> AbstractAuth:
    """Fixture for mock auth."""
    return MockAuth(AsyncMock(), "http://localhost")


@pytest.fixture
def mock_websession() -> MagicMock:
    """Fixture for mock aiohttp ClientSession."""
    session = MagicMock(spec=aiohttp.ClientSession)
    session.request = AsyncMock()
    return session


async def test_auth_token_client_error(
    mock_websession: MagicMock,
) -> None:
    """Test HealthAuthException when async_get_access_token raises ClientError."""
    auth = AsyncMock(spec=AbstractAuth)
    auth.async_get_access_token.side_effect = ClientError("Token error")
    session = GoogleHealthSession(auth, mock_websession)

    with pytest.raises(HealthAuthException, match="Access token failure: Token error"):
        await session.get("v1/user/profile")


async def test_request_headers_and_url_formatting(
    mock_auth: AbstractAuth, mock_websession: MagicMock
) -> None:
    """Test header injection, absolute URL preservation, and HTTP verb helpers."""
    mock_response = AsyncMock(spec=aiohttp.ClientResponse)
    mock_response.status = 200
    mock_websession.request.return_value = mock_response

    session = GoogleHealthSession(
        mock_auth, mock_websession, host="https://health.googleapis.com"
    )

    # 1. GET with relative URL (no auth header passed)
    resp = await session.get("v1/test")
    assert resp == mock_response
    mock_websession.request.assert_called_with(
        "GET",
        "https://health.googleapis.com/v1/test",
        headers={"Authorization": "Bearer test-token"},
    )

    # 2. POST with absolute URL, custom headers, and json body
    await session.post(
        "https://custom.api/v1/test",
        headers={"Authorization": "Bearer existing"},
        json={"data": 1},
    )
    mock_websession.request.assert_called_with(
        "POST",
        "https://custom.api/v1/test",
        json={"data": 1},
        headers={"Authorization": "Bearer existing"},
    )

    # 3. PATCH helper
    await session.patch("v1/test", json={"patch": "value"})
    mock_websession.request.assert_called_with(
        "PATCH",
        "https://health.googleapis.com/v1/test",
        json={"patch": "value"},
        headers={"Authorization": "Bearer test-token"},
    )

    # 4. DELETE helper
    await session.delete("v1/test")
    mock_websession.request.assert_called_with(
        "DELETE",
        "https://health.googleapis.com/v1/test",
        headers={"Authorization": "Bearer test-token"},
    )


async def test_raise_for_status_unauthorized(
    mock_auth: AbstractAuth, mock_websession: MagicMock
) -> None:
    """Test 401 Unauthorized response raises HealthAuthException."""
    mock_response = AsyncMock(spec=aiohttp.ClientResponse)
    mock_response.status = 401
    mock_response.text.return_value = '{"error": {"code": 401, "message": "Invalid credentials", "status": "UNAUTHENTICATED"}}'

    request_info = MagicMock()
    mock_response.raise_for_status.side_effect = ClientResponseError(
        request_info=request_info,
        history=(),
        status=HTTPStatus.UNAUTHORIZED,
        message="Unauthorized",
    )
    mock_websession.request.return_value = mock_response

    session = GoogleHealthSession(mock_auth, mock_websession)
    with pytest.raises(
        HealthAuthException,
        match="Unauthorized response from API \\(401\\): UNAUTHENTICATED: \\(401\\): Invalid credentials",
    ):
        await session.get("v1/test")


async def test_raise_for_status_forbidden(
    mock_auth: AbstractAuth, mock_websession: MagicMock
) -> None:
    """Test 403 Forbidden response raises HealthApiForbiddenException."""
    mock_response = AsyncMock(spec=aiohttp.ClientResponse)
    mock_response.status = 403
    mock_response.text.return_value = '{"error": {"code": 403, "message": "Permission denied", "status": "PERMISSION_DENIED"}}'

    request_info = MagicMock()
    mock_response.raise_for_status.side_effect = ClientResponseError(
        request_info=request_info,
        history=(),
        status=HTTPStatus.FORBIDDEN,
        message="Forbidden",
    )
    mock_websession.request.return_value = mock_response

    session = GoogleHealthSession(mock_auth, mock_websession)
    with pytest.raises(
        HealthApiForbiddenException,
        match="Forbidden response from API \\(403\\): PERMISSION_DENIED: \\(403\\): Permission denied",
    ):
        await session.get("v1/test")


async def test_raise_for_status_generic_client_response_error(
    mock_auth: AbstractAuth, mock_websession: MagicMock
) -> None:
    """Test generic status error (e.g. 500) raises HealthApiException."""
    mock_response = AsyncMock(spec=aiohttp.ClientResponse)
    mock_response.status = 500
    mock_response.text.return_value = (
        '{"error": {"code": 500, "message": "Server Error", "status": "INTERNAL"}}'
    )

    request_info = MagicMock()
    mock_response.raise_for_status.side_effect = ClientResponseError(
        request_info=request_info,
        history=(),
        status=HTTPStatus.INTERNAL_SERVER_ERROR,
        message="Internal Server Error",
    )
    mock_websession.request.return_value = mock_response

    session = GoogleHealthSession(mock_auth, mock_websession)
    with pytest.raises(
        HealthApiException,
        match="Internal Server Error response from API \\(500\\): INTERNAL: \\(500\\): Server Error",
    ):
        await session.get("v1/test")


async def test_raise_for_status_generic_client_error(
    mock_auth: AbstractAuth, mock_websession: MagicMock
) -> None:
    """Test generic aiohttp ClientError raises HealthApiException."""
    mock_response = AsyncMock(spec=aiohttp.ClientResponse)
    mock_response.status = 200
    mock_response.raise_for_status.side_effect = ClientError("Connection reset")
    mock_websession.request.return_value = mock_response

    session = GoogleHealthSession(mock_auth, mock_websession)
    with pytest.raises(HealthApiException, match="Error from API: Connection reset"):
        await session.get("v1/test")


async def test_error_detail_variations() -> None:
    """Test _error_detail parsing under various status codes and JSON formats."""
    # 1. Status < 400 -> None
    resp_200 = AsyncMock(spec=aiohttp.ClientResponse)
    resp_200.status = 200
    assert await GoogleHealthSession._error_detail(resp_200) is None

    # 2. Status >= 400 but text() raises ClientError -> None
    resp_error_text = AsyncMock(spec=aiohttp.ClientResponse)
    resp_error_text.status = 400
    resp_error_text.text.side_effect = ClientError("Stream closed")
    assert await GoogleHealthSession._error_detail(resp_error_text) is None

    # 3. Valid JSON with partial error fields
    # Only status
    resp_status_only = AsyncMock(spec=aiohttp.ClientResponse)
    resp_status_only.status = 400
    resp_status_only.text.return_value = '{"error": {"status": "INVALID"}}'
    assert await GoogleHealthSession._error_detail(resp_status_only) == "INVALID"

    # Only code
    resp_code_only = AsyncMock(spec=aiohttp.ClientResponse)
    resp_code_only.status = 400
    resp_code_only.text.return_value = '{"error": {"code": 404}}'
    assert await GoogleHealthSession._error_detail(resp_code_only) == "(404)"

    # Only message
    resp_msg_only = AsyncMock(spec=aiohttp.ClientResponse)
    resp_msg_only.status = 400
    resp_msg_only.text.return_value = '{"error": {"message": "Resource not found"}}'
    assert (
        await GoogleHealthSession._error_detail(resp_msg_only) == "Resource not found"
    )

    # Empty error object -> None
    resp_empty_error = AsyncMock(spec=aiohttp.ClientResponse)
    resp_empty_error.status = 400
    resp_empty_error.text.return_value = '{"error": {}}'
    assert await GoogleHealthSession._error_detail(resp_empty_error) is None

    # 4. Invalid JSON / HTML response -> None
    resp_html = AsyncMock(spec=aiohttp.ClientResponse)
    resp_html.status = 502
    resp_html.text.return_value = "<html>Bad Gateway</html>"
    assert await GoogleHealthSession._error_detail(resp_html) is None
