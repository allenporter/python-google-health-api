"""HTTP Client session wrapper for the Google Health API."""

import logging
from http import HTTPStatus
from typing import Any

import aiohttp
from aiohttp.client_exceptions import ClientError

from .auth import AbstractAuth
from .const import HEALTH_API_URL
from .exceptions import (
    HealthApiException,
    HealthApiForbiddenException,
    HealthAuthException,
)
from .model.base import ErrorResponse

_LOGGER = logging.getLogger(__name__)
AUTHORIZATION_HEADER = "Authorization"


class GoogleHealthSession:
    """Session wrapper that handles authentication and network requests."""

    def __init__(
        self,
        auth: AbstractAuth,
        websession: aiohttp.ClientSession,
        host: str | None = None,
    ) -> None:
        """Initialize the session."""
        self._auth = auth
        self._websession = websession
        self._host = host or HEALTH_API_URL
        self._timezone_cache: dict[str, str] = {}

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
        error_detail = await cls._error_detail(resp)
        try:
            resp.raise_for_status()
        except aiohttp.ClientResponseError as err:
            error_message = f"{err.message} response from API ({resp.status})"
            if error_detail:
                error_message += f": {error_detail}"
            if err.status == HTTPStatus.FORBIDDEN:
                raise HealthApiForbiddenException(error_message)
            if err.status == HTTPStatus.UNAUTHORIZED:
                raise HealthAuthException(error_message)
            raise HealthApiException(error_message) from err
        except aiohttp.ClientError as err:
            raise HealthApiException(f"Error from API: {err}") from err
        return resp

    @classmethod
    async def _error_detail(cls, resp: aiohttp.ClientResponse) -> str | None:
        """Returns an error message string from the API response."""
        if resp.status < 400:
            return None
        try:
            result = await resp.text()
        except ClientError:
            return None

        try:
            error_response = ErrorResponse.from_json(result)
            if error_response and error_response.error:
                error_obj = error_response.error
                msg = error_obj.message
                status = error_obj.status
                code = error_obj.code
                parts = []
                if status:
                    parts.append(status)
                if code:
                    parts.append(f"({code})")
                if msg:
                    parts.append(msg)
                if parts:
                    return ": ".join(parts)
        except (ValueError, TypeError):
            pass
        return None
