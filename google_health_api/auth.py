"""API for Google Health OAuth."""

from abc import ABC, abstractmethod

import aiohttp

from .const import HEALTH_API_URL


class AbstractAuth(ABC):
    """Base class for Google Health authentication library."""

    def __init__(
        self, websession: aiohttp.ClientSession, host: str | None = None
    ) -> None:
        """Initialize the auth."""
        self._websession = websession
        self._host = host or HEALTH_API_URL

    @abstractmethod
    async def async_get_access_token(self) -> str:
        """Return a valid access token."""
