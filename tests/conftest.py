"""Shared fixtures and fake authentication implementation for tests."""

from collections.abc import Awaitable, Callable
from pathlib import Path

import aiohttp
import pytest
from aiohttp import ClientSession
from aiohttp.web import Application

from google_health_api.auth import AbstractAuth

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def load_fixture(fixture_path: str) -> str:
    """Load a fixture file relative to tests/fixtures/."""
    return (FIXTURES_DIR / fixture_path).read_text(encoding="utf-8")


PATH_PREFIX = "/path-prefix"

AuthCallback = Callable[
    [
        list[
            tuple[
                str,
                str,
                Callable[[aiohttp.web.Request], Awaitable[aiohttp.web.Response]],
            ]
        ]
    ],
    Awaitable[AbstractAuth],
]


class FakeAuth(AbstractAuth):
    """Implementation of AbstractAuth for use in tests."""

    async def async_get_access_token(self) -> str:
        """Return a fake OAuth access token."""
        return "fake-oauth-token"


@pytest.fixture(name="auth_cb")
def mock_auth_fixture(
    aiohttp_client: Callable[[Application], Awaitable[ClientSession]],
) -> AuthCallback:
    """Fixture to dynamically create authenticated clients with fake endpoints."""

    async def create_auth(
        handlers: list[
            tuple[
                str,
                str,
                Callable[[aiohttp.web.Request], Awaitable[aiohttp.web.Response]],
            ]
        ],
    ) -> AbstractAuth:
        """Create a test authentication wrapper routing to specifies request handlers."""
        app = Application()
        for method, path, handler in handlers:
            method_upper = method.upper()
            if method_upper == "GET":
                app.router.add_get(f"{PATH_PREFIX}/{path}", handler)
            elif method_upper == "POST":
                app.router.add_post(f"{PATH_PREFIX}/{path}", handler)
            elif method_upper == "PATCH":
                app.router.add_patch(f"{PATH_PREFIX}/{path}", handler)
            elif method_upper == "DELETE":
                app.router.add_delete(f"{PATH_PREFIX}/{path}", handler)

        client = await aiohttp_client(app)
        return FakeAuth(client, PATH_PREFIX)

    return create_auth
