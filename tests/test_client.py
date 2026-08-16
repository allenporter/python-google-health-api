"""Tests for google_health_api/client.py."""

from http import HTTPStatus
from unittest.mock import AsyncMock, MagicMock

import aiohttp
import pytest
from aiohttp import ClientError, ClientResponseError

from google_health_api.auth import AbstractAuth
from google_health_api.client import GoogleHealthSession, error_detail
from google_health_api.exceptions import (
    GoogleHealthApiError,
    HealthApiConnectionException,
    HealthApiException,
    HealthApiForbiddenException,
    HealthApiRateLimitException,
    HealthApiScopeInsufficientException,
    HealthApiServiceDisabledException,
    HealthAuthException,
)

from .conftest import load_fixture


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
    """Test generic aiohttp ClientError raises HealthApiConnectionException."""
    mock_response = AsyncMock(spec=aiohttp.ClientResponse)
    mock_response.status = 200
    mock_response.raise_for_status.side_effect = ClientError("Connection reset")
    mock_websession.request.return_value = mock_response

    session = GoogleHealthSession(mock_auth, mock_websession)
    with pytest.raises(
        HealthApiConnectionException, match="Error from API: Connection reset"
    ):
        await session.get("v1/test")


@pytest.mark.asyncio
async def test_error_detail_status_less_than_400() -> None:
    """Test that error_detail returns None for success status codes (< 400)."""
    resp = AsyncMock(spec=aiohttp.ClientResponse)
    resp.status = 200
    assert await error_detail(resp) is None


@pytest.mark.asyncio
async def test_error_detail_text_raises_client_error() -> None:
    """Test that error_detail returns None when retrieving response text raises ClientError."""
    resp = AsyncMock(spec=aiohttp.ClientResponse)
    resp.status = 400
    resp.text.side_effect = ClientError("Stream closed")
    assert await error_detail(resp) is None


@pytest.mark.parametrize(
    ("status", "payload", "expected"),
    [
        (400, '{"error": {"status": "INVALID"}}', "INVALID"),
        (400, '{"error": {"code": 404}}', "(404)"),
        (400, '{"error": {"message": "Resource not found"}}', "Resource not found"),
        (
            400,
            '{"error": {"status": "INVALID", "code": 400, "message": "Bad request"}}',
            "INVALID: (400): Bad request",
        ),
        (400, '{"error": {}}', None),
        (502, "<html>Bad Gateway</html>", None),
        (400, "not json", None),
    ],
)
@pytest.mark.asyncio
async def test_error_detail_json_variations(
    status: int, payload: str, expected: str | None
) -> None:
    """Test error_detail parsing with various JSON structures and invalid payloads."""
    resp = AsyncMock(spec=aiohttp.ClientResponse)
    resp.status = status
    resp.text.return_value = payload
    assert await error_detail(resp) == expected


@pytest.mark.parametrize(
    ("fixture_file", "http_status", "expected_exc"),
    [
        (
            "errors/service_disabled.json",
            HTTPStatus.FORBIDDEN,
            HealthApiServiceDisabledException,
        ),
        (
            "errors/access_token_scope_insufficient.json",
            HTTPStatus.FORBIDDEN,
            HealthApiScopeInsufficientException,
        ),
        (
            "errors/oauth_insufficient_scope.json",
            HTTPStatus.FORBIDDEN,
            HealthApiScopeInsufficientException,
        ),
        (
            "errors/oauth_invalid_token.json",
            HTTPStatus.UNAUTHORIZED,
            HealthAuthException,
        ),
        (
            "errors/unauthenticated.json",
            HTTPStatus.UNAUTHORIZED,
            HealthAuthException,
        ),
        (
            "errors/resource_exhausted.json",
            HTTPStatus.TOO_MANY_REQUESTS,
            HealthApiRateLimitException,
        ),
        (
            "errors/permission_denied.json",
            HTTPStatus.FORBIDDEN,
            HealthApiForbiddenException,
        ),
    ],
)
@pytest.mark.asyncio
async def test_raise_for_status_fixtures(
    mock_auth: AbstractAuth,
    mock_websession: MagicMock,
    fixture_file: str,
    http_status: HTTPStatus,
    expected_exc: type[GoogleHealthApiError],
) -> None:
    """Test specific exception raising with realistic JSON fixtures."""
    payload = load_fixture(fixture_file)
    mock_response = AsyncMock(spec=aiohttp.ClientResponse)
    mock_response.status = http_status
    mock_response.text.return_value = payload

    request_info = MagicMock()
    mock_response.raise_for_status.side_effect = ClientResponseError(
        request_info=request_info,
        history=(),
        status=http_status,
        message=http_status.phrase,
    )
    mock_websession.request.return_value = mock_response

    session = GoogleHealthSession(mock_auth, mock_websession)
    with pytest.raises(expected_exc):
        await session.get("v1/test")
