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


class ServiceAccountAuth(AbstractAuth):
    """Authentication using a Google Service Account key file."""

    def __init__(
        self,
        websession: aiohttp.ClientSession,
        json_path: str,
        subject: str | None = None,
        scopes: list[str] | None = None,
        host: str | None = None,
    ) -> None:
        """Initialize ServiceAccountAuth.

        Args:
            websession: aiohttp ClientSession.
            json_path: Path to the service account JSON key file.
            subject: User email to impersonate (if using Domain-Wide Delegation).
            scopes: OAuth scopes to request (defaults to all Google Health read/write scopes).
            host: API host URL.
        """
        super().__init__(websession, host)
        try:
            from google.oauth2 import service_account
        except ImportError as err:
            raise ImportError(
                "google-auth library is required for ServiceAccountAuth. "
                "Install it using: pip install google-auth"
            ) from err

        if scopes is None:
            scopes = [
                "https://www.googleapis.com/auth/health.steps.read",
                "https://www.googleapis.com/auth/health.steps.write",
                "https://www.googleapis.com/auth/health.heart-rate.read",
                "https://www.googleapis.com/auth/health.heart-rate.write",
            ]

        self._credentials = service_account.Credentials.from_service_account_file(
            json_path,
            scopes=scopes,
            subject=subject,
        )

    async def async_get_access_token(self) -> str:
        """Fetch and return a valid access token."""
        import asyncio
        from google.auth.transport.requests import Request

        loop = asyncio.get_running_loop()
        req = Request()
        # Credentials refresh is synchronous and involves disk/network I/O, so run in an executor
        await loop.run_in_executor(None, self._credentials.refresh, req)
        return self._credentials.token
