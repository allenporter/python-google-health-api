"""HTTP Client session wrapper for the Google Health API."""

import json
import logging
from dataclasses import dataclass
from http import HTTPStatus
from typing import Any

import aiohttp
from aiohttp.client_exceptions import ClientError

from .auth import AbstractAuth
from .const import HEALTH_API_URL, USERINFO_API_URL
from .exceptions import (
    GoogleHealthApiError,
    HealthApiConnectionException,
    HealthApiException,
    HealthApiForbiddenException,
    HealthApiNotFoundException,
    HealthApiRateLimitException,
    HealthApiScopeInsufficientException,
    HealthApiServiceDisabledException,
    HealthAuthException,
)

_LOGGER = logging.getLogger(__name__)
AUTHORIZATION_HEADER = "Authorization"

RPC_REASON_EXCEPTIONS: dict[str, type[GoogleHealthApiError]] = {
    "SERVICE_DISABLED": HealthApiServiceDisabledException,
    "ACCESS_TOKEN_SCOPE_INSUFFICIENT": HealthApiScopeInsufficientException,
    "RATE_LIMIT_EXCEEDED": HealthApiRateLimitException,
    "QUOTA_EXCEEDED": HealthApiRateLimitException,
}

OAUTH_ERROR_EXCEPTIONS: dict[str, type[GoogleHealthApiError]] = {
    "insufficient_scope": HealthApiScopeInsufficientException,
    "invalid_token": HealthAuthException,
    "access_denied": HealthApiForbiddenException,
}

HTTP_STATUS_EXCEPTIONS: dict[int, type[GoogleHealthApiError]] = {
    HTTPStatus.UNAUTHORIZED: HealthAuthException,
    HTTPStatus.FORBIDDEN: HealthApiForbiddenException,
    HTTPStatus.NOT_FOUND: HealthApiNotFoundException,
    HTTPStatus.TOO_MANY_REQUESTS: HealthApiRateLimitException,
}


@dataclass
class ParsedErrorInfo:
    """Parsed error information from an API response."""

    detail: str | None = None
    exception_cls: type[GoogleHealthApiError] = HealthApiException


class GoogleHealthSession:
    """Session wrapper that handles authentication and network requests."""

    def __init__(
        self,
        auth: AbstractAuth,
        websession: aiohttp.ClientSession,
        host: str | None = None,
        user_info_url: str | None = None,
    ) -> None:
        """Initialize the session."""
        self._auth = auth
        self._websession = websession
        self._host = host or HEALTH_API_URL
        self._timezone_cache: dict[str, str] = {}
        self.user_info_url = user_info_url or USERINFO_API_URL

    async def request(
        self,
        method: str,
        url: str,
        headers: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> aiohttp.ClientResponse:
        """Make an authenticated request."""
        try:
            access_token = await self._auth.async_get_access_token()
        except ClientError as err:
            raise HealthAuthException(f"Access token failure: {err}") from err

        if headers is None:
            headers = {}
        if AUTHORIZATION_HEADER not in headers:
            headers[AUTHORIZATION_HEADER] = f"Bearer {access_token}"

        if not url.startswith(("http://", "https://")):
            url = f"{self._host}/{url}"

        _LOGGER.debug("request[%s]=%s %s", method, url, kwargs.get("params"))
        if method != "get" and "json" in kwargs:
            _LOGGER.debug("request[post json]=%s", kwargs["json"])

        resp = await self._websession.request(method, url, **kwargs, headers=headers)
        return await self._raise_for_status(resp)

    async def get(self, url: str, **kwargs: Any) -> aiohttp.ClientResponse:
        """Make a GET request."""
        return await self.request("GET", url, **kwargs)

    async def post(self, url: str, **kwargs: Any) -> aiohttp.ClientResponse:
        """Make a POST request."""
        return await self.request("POST", url, **kwargs)

    async def patch(self, url: str, **kwargs: Any) -> aiohttp.ClientResponse:
        """Make a PATCH request."""
        return await self.request("PATCH", url, **kwargs)

    async def delete(self, url: str, **kwargs: Any) -> aiohttp.ClientResponse:
        """Make a DELETE request."""
        return await self.request("DELETE", url, **kwargs)

    @classmethod
    async def _raise_for_status(
        cls, resp: aiohttp.ClientResponse
    ) -> aiohttp.ClientResponse:
        """Raise exceptions on failure methods."""
        error_info = await parse_error_response(resp)
        try:
            resp.raise_for_status()
        except aiohttp.ClientResponseError as err:
            error_message = f"{err.message} response from API ({resp.status})"
            if error_info.detail:
                error_message += f": {error_info.detail}"
            raise error_info.exception_cls(error_message) from err
        except aiohttp.ClientError as err:
            raise HealthApiConnectionException(f"Error from API: {err}") from err
        return resp


def _parse_rpc_error(
    error: dict[str, Any],
) -> tuple[str | None, type[GoogleHealthApiError] | None]:
    """Extract detail string and specific exception from a Google RPC error dict."""
    exc_cls: type[GoogleHealthApiError] | None = None
    for detail in error.get("details", []):
        if (
            isinstance(detail, dict)
            and (reason := detail.get("reason"))
            and (exc_cls := RPC_REASON_EXCEPTIONS.get(reason))
        ):
            break

    parts: list[str] = []
    if status := error.get("status"):
        parts.append(str(status))
    if (code := error.get("code")) is not None:
        parts.append(f"({code})")
    if msg := error.get("message"):
        parts.append(str(msg))

    return (": ".join(parts) if parts else None), exc_cls


def _parse_oauth_error(
    data: dict[str, Any],
) -> tuple[str | None, type[GoogleHealthApiError] | None]:
    """Extract detail string and specific exception from an OAuth 2.0 error dict."""
    error = str(data.get("error"))
    desc = data.get("error_description")
    detail = f"{error}: {desc}" if desc else error
    return detail, OAUTH_ERROR_EXCEPTIONS.get(error)


async def parse_error_response(resp: aiohttp.ClientResponse) -> ParsedErrorInfo:
    """Parse error details and determine the specific exception class from the API response."""
    if resp.status < 400:
        return ParsedErrorInfo()

    detail: str | None = None
    exception_cls: type[GoogleHealthApiError] | None = None

    try:
        raw_data = json.loads(await resp.text())
        if isinstance(raw_data, dict):
            error_val = raw_data.get("error")
            if isinstance(error_val, dict):
                detail, exception_cls = _parse_rpc_error(error_val)
            elif isinstance(error_val, str):
                detail, exception_cls = _parse_oauth_error(raw_data)
    except (ClientError, ValueError, TypeError):
        pass

    fallback_cls = exception_cls or HTTP_STATUS_EXCEPTIONS.get(
        resp.status, HealthApiException
    )
    return ParsedErrorInfo(detail=detail, exception_cls=fallback_cls)


async def error_detail(resp: aiohttp.ClientResponse) -> str | None:
    """Returns an error message string from the API response."""
    info = await parse_error_response(resp)
    return info.detail
