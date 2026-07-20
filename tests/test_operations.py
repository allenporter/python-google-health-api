"""Tests for the Operations sub-API and PendingOperation."""

from collections.abc import AsyncGenerator
from typing import Any

import aiohttp
import pytest

from google_health_api.api import GoogleHealthApi, PendingOperation
from google_health_api.exceptions import OperationError
from google_health_api.model import Operation
from .conftest import AuthCallback


@pytest.fixture(name="api_responses")
def mock_api_responses() -> dict[str, list[dict[str, Any]]]:
    """Fixture for tracking mock responses by key."""
    return {
        "operation_get": [],
        "subscriber_create": [],
    }


@pytest.fixture(name="requests")
def mock_requests() -> list[dict[str, Any]]:
    """Fixture for capturing requests."""
    return []


@pytest.fixture(name="api")
async def mock_api(
    auth_cb: AuthCallback,
    requests: list[dict[str, Any]],
    api_responses: dict[str, list[dict[str, Any]]],
) -> AsyncGenerator[GoogleHealthApi, None]:
    """Fixture to create the mock GoogleHealthApi client with operation endpoints."""

    async def get_operation_handler(
        request: aiohttp.web.Request,
    ) -> aiohttp.web.Response:
        requests.append(
            {
                "method": "GET",
                "url": str(request.url),
                "query": dict(request.query),
            }
        )
        return aiohttp.web.json_response(api_responses["operation_get"].pop(0))

    async def create_subscriber_handler(
        request: aiohttp.web.Request,
    ) -> aiohttp.web.Response:
        body = await request.json()
        requests.append(
            {
                "method": "POST",
                "url": str(request.url),
                "body": body,
                "query": dict(request.query),
            }
        )
        return aiohttp.web.json_response(api_responses["subscriber_create"].pop(0))

    auth = await auth_cb(
        [
            (
                "GET",
                "v4/projects/test-project/operations/op-123",
                get_operation_handler,
            ),
            (
                "POST",
                "v4/projects/test-project/subscribers",
                create_subscriber_handler,
            ),
        ]
    )
    yield GoogleHealthApi(auth)


async def test_get_operation(
    api: GoogleHealthApi,
    requests: list[dict[str, Any]],
    api_responses: dict[str, list[dict[str, Any]]],
) -> None:
    """Test retrieving an operation by name."""
    api_responses["operation_get"].append(
        {
            "name": "projects/test-project/operations/op-123",
            "done": False,
        }
    )

    result = await api.operations.get("projects/test-project/operations/op-123")

    assert isinstance(result, Operation)
    assert result.name == "projects/test-project/operations/op-123"
    assert result.done is False
    assert len(requests) == 1
    assert requests[0]["method"] == "GET"


async def test_get_operation_done_with_response(
    api: GoogleHealthApi,
    requests: list[dict[str, Any]],
    api_responses: dict[str, list[dict[str, Any]]],
) -> None:
    """Test retrieving a completed operation with a response payload."""
    api_responses["operation_get"].append(
        {
            "name": "projects/test-project/operations/op-123",
            "done": True,
            "response": {"endpointUri": "https://example.com/webhook"},
        }
    )

    result = await api.operations.get("projects/test-project/operations/op-123")

    assert result.done is True
    assert result.response == {"endpointUri": "https://example.com/webhook"}
    assert result.error is None


async def test_wait_already_done(
    api: GoogleHealthApi,
    requests: list[dict[str, Any]],
    api_responses: dict[str, list[dict[str, Any]]],
) -> None:
    """Test waiting on an operation that is already done returns immediately."""
    operation = Operation(
        name="projects/test-project/operations/op-123",
        done=True,
    )

    result = await api.operations.wait(operation, poll_interval=0)

    assert result.done is True
    assert result.name == "projects/test-project/operations/op-123"
    # No GET request should be made since it was already done
    assert len(requests) == 0


async def test_wait_polls_until_done(
    api: GoogleHealthApi,
    requests: list[dict[str, Any]],
    api_responses: dict[str, list[dict[str, Any]]],
) -> None:
    """Test waiting polls the operation until done becomes True."""
    # First poll: still running
    api_responses["operation_get"].append(
        {
            "name": "projects/test-project/operations/op-123",
            "done": False,
        }
    )
    # Second poll: done
    api_responses["operation_get"].append(
        {
            "name": "projects/test-project/operations/op-123",
            "done": True,
            "response": {"endpointUri": "https://example.com/webhook"},
        }
    )

    operation = Operation(
        name="projects/test-project/operations/op-123",
        done=False,
    )

    result = await api.operations.wait(operation, poll_interval=0)

    assert result.done is True
    assert result.response == {"endpointUri": "https://example.com/webhook"}
    # Should have made 2 GET requests
    assert len(requests) == 2
    assert all(r["method"] == "GET" for r in requests)


async def test_wait_operation_error(
    api: GoogleHealthApi,
    requests: list[dict[str, Any]],
    api_responses: dict[str, list[dict[str, Any]]],
) -> None:
    """Test that wait raises OperationError when the operation fails."""
    api_responses["operation_get"].append(
        {
            "name": "projects/test-project/operations/op-123",
            "done": True,
            "error": {
                "code": 400,
                "message": "Invalid endpoint URI",
            },
        }
    )

    operation = Operation(
        name="projects/test-project/operations/op-123",
        done=False,
    )

    with pytest.raises(OperationError) as exc_info:
        await api.operations.wait(operation, poll_interval=0)

    assert exc_info.value.status.code == 400
    assert exc_info.value.status.message == "Invalid endpoint URI"
    assert "Invalid endpoint URI" in str(exc_info.value)


async def test_wait_timeout(
    api: GoogleHealthApi,
    requests: list[dict[str, Any]],
    api_responses: dict[str, list[dict[str, Any]]],
) -> None:
    """Test that wait raises TimeoutError when the operation never completes."""
    # Queue enough not-done responses for the short timeout window
    for _ in range(1000):
        api_responses["operation_get"].append(
            {
                "name": "projects/test-project/operations/op-123",
                "done": False,
            }
        )

    operation = Operation(
        name="projects/test-project/operations/op-123",
        done=False,
    )

    with pytest.raises(TimeoutError):
        await api.operations.wait(operation, poll_interval=0, timeout=0.01)


async def test_pending_operation_properties(
    api: GoogleHealthApi,
    requests: list[dict[str, Any]],
    api_responses: dict[str, list[dict[str, Any]]],
) -> None:
    """Test that PendingOperation exposes name and the initial operation snapshot."""
    api_responses["subscriber_create"].append(
        {
            "name": "projects/test-project/operations/op-123",
            "done": False,
            "metadata": {"@type": "type.googleapis.com/some.Type"},
        }
    )

    result = await api.subscribers.create(
        project="test-project",
        endpoint_uri="https://example.com/webhook",
        endpoint_authorization_secret="secret",
    )

    assert isinstance(result, PendingOperation)
    assert result.name == "projects/test-project/operations/op-123"
    # The initial snapshot is accessible via .operation
    assert isinstance(result.operation, Operation)
    assert result.operation.name == result.name
    assert result.operation.done is False
    assert result.operation.metadata == {"@type": "type.googleapis.com/some.Type"}


async def test_pending_operation_wait(
    api: GoogleHealthApi,
    requests: list[dict[str, Any]],
    api_responses: dict[str, list[dict[str, Any]]],
) -> None:
    """Test that PendingOperation.wait() polls and returns the final Operation."""
    # Create subscriber returns pending operation
    api_responses["subscriber_create"].append(
        {
            "name": "projects/test-project/operations/op-123",
            "done": False,
        }
    )
    # First poll: still running
    api_responses["operation_get"].append(
        {
            "name": "projects/test-project/operations/op-123",
            "done": False,
        }
    )
    # Second poll: done
    api_responses["operation_get"].append(
        {
            "name": "projects/test-project/operations/op-123",
            "done": True,
            "response": {"endpointUri": "https://example.com/webhook"},
        }
    )

    pending = await api.subscribers.create(
        project="test-project",
        endpoint_uri="https://example.com/webhook",
        endpoint_authorization_secret="secret",
    )

    completed = await pending.wait(poll_interval=0)

    assert isinstance(completed, Operation)
    assert completed.done is True
    assert completed.response == {"endpointUri": "https://example.com/webhook"}
    # 1 POST (create) + 2 GETs (poll)
    assert len(requests) == 3
