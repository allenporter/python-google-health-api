"""API for Google Health OAuth."""

import logging
from abc import ABC, abstractmethod
from http import HTTPStatus
from typing import Any, TypeVar

import aiohttp
from aiohttp.client_exceptions import ClientError
from mashumaro.mixins.json import DataClassJSONMixin

from .const import HEALTH_API_URL
from .exceptions import (
    HealthApiException,
    HealthApiForbiddenException,
    HealthAuthException,
)

_LOGGER = logging.getLogger(__name__)

AUTHORIZATION_HEADER = "Authorization"

_T = TypeVar("_T", bound=DataClassJSONMixin)


class AbstractAuth(ABC):
    """Base class for Google Health authentication library.

    Provides an asyncio interface around HTTP requests with auth headers.
    """

    def __init__(
        self, websession: aiohttp.ClientSession, host: str | None = None
    ) -> None:
        """Initialize the auth."""
        self._websession = websession
        self._host = host or HEALTH_API_URL

    @abstractmethod
    async def async_get_access_token(self) -> str:
        """Return a valid access token."""

    async def request(
        self,
        method: str,
        url: str,
        headers: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> aiohttp.ClientResponse:
        """Make a request."""
        try:
            access_token = await self.async_get_access_token()
        except ClientError as err:
            raise HealthAuthException(f"Access token failure: {err}") from err
        if headers is None:
            headers = {}
        if AUTHORIZATION_HEADER not in headers:
            headers[AUTHORIZATION_HEADER] = f"Bearer {access_token}"
        if not (url.startswith("http://") or url.startswith("https://")):
            url = f"{self._host}/{url}"
        _LOGGER.debug("request[%s]=%s %s", method, url, kwargs.get("params"))
        if method != "get" and "json" in kwargs:
            _LOGGER.debug("request[post json]=%s", kwargs["json"])
        return await self._websession.request(method, url, **kwargs, headers=headers)

    async def get(self, url: str, **kwargs: Any) -> aiohttp.ClientResponse:
        """Make a get request."""
        try:
            resp = await self.request("get", url, **kwargs)
        except ClientError as err:
            raise HealthApiException(f"Error connecting to API: {err}") from err
        return await AbstractAuth._raise_for_status(resp)

    async def get_json(
        self,
        url: str,
        data_cls: type[_T],
        **kwargs: Any,
    ) -> _T:
        """Make a get request and return json response."""
        resp = await self.get(url, **kwargs)
        try:
            result = await resp.text()
        except ClientError as err:
            raise HealthApiException("Server returned malformed response") from err
        _LOGGER.debug("response=%s", result)
        try:
            return data_cls.from_json(result)
        except (LookupError, ValueError) as err:
            raise HealthApiException(
                f"Server return malformed response: {result}"
            ) from err

    async def post(self, url: str, **kwargs: Any) -> aiohttp.ClientResponse:
        """Make a post request."""
        try:
            resp = await self.request("post", url, **kwargs)
        except ClientError as err:
            raise HealthApiException(f"Error connecting to API: {err}") from err
        return await AbstractAuth._raise_for_status(resp)

    async def post_json(self, url: str, data_cls: type[_T], **kwargs: Any) -> _T:
        """Make a post request and return a json response."""
        resp = await self.post(url, **kwargs)
        try:
            result = await resp.text()
        except ClientError as err:
            raise HealthApiException("Server returned malformed response") from err
        _LOGGER.debug("response=%s", result)
        try:
            return data_cls.from_json(result)
        except (LookupError, ValueError) as err:
            raise HealthApiException(
                f"Server return malformed response: {result}"
            ) from err

    async def patch(self, url: str, **kwargs: Any) -> aiohttp.ClientResponse:
        """Make a patch request."""
        try:
            resp = await self.request("patch", url, **kwargs)
        except ClientError as err:
            raise HealthApiException(f"Error connecting to API: {err}") from err
        return await AbstractAuth._raise_for_status(resp)

    async def patch_json(self, url: str, data_cls: type[_T], **kwargs: Any) -> _T:
        """Make a patch request and return a json response."""
        resp = await self.patch(url, **kwargs)
        try:
            result = await resp.text()
        except ClientError as err:
            raise HealthApiException("Server returned malformed response") from err
        _LOGGER.debug("response=%s", result)
        try:
            return data_cls.from_json(result)
        except (LookupError, ValueError) as err:
            raise HealthApiException(
                f"Server return malformed response: {result}"
            ) from err

    async def delete(self, url: str, **kwargs: Any) -> aiohttp.ClientResponse:
        """Make a delete request."""
        try:
            resp = await self.request("delete", url, **kwargs)
        except ClientError as err:
            raise HealthApiException(f"Error connecting to API: {err}") from err
        return await AbstractAuth._raise_for_status(resp)

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

        # Parse error message manually to avoid circular dependencies with model files in Phase 1
        try:
            import json

            error_data = json.loads(result)
            error_obj = error_data.get("error", {})
            if isinstance(error_obj, dict):
                msg = error_obj.get("message")
                status = error_obj.get("status")
                code = error_obj.get("code")
                parts = []
                if status:
                    parts.append(status)
                if code:
                    parts.append(f"({code})")
                if msg:
                    parts.append(msg)
                if parts:
                    return ": ".join(parts)
        except (ValueError, TypeError, json.JSONDecodeError):
            pass
        return None
