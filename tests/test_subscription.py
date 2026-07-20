"""Tests for webhook subscribers and subscriptions API endpoints."""

from collections.abc import AsyncGenerator
from typing import Any
import aiohttp
import pytest

from google_health_api.api import GoogleHealthApi
from google_health_api.model import (
    EndpointAuthorization,
    Subscriber,
    SubscriberConfig,
    Subscription,
)
from .conftest import AuthCallback


@pytest.fixture(name="api_responses")
def mock_api_responses() -> dict[str, list[dict[str, Any]]]:
    """Fixture for tracking mock responses by path/method key."""
    return {
        "subscriber_create": [],
        "subscriber_patch": [],
        "subscriber_list": [],
        "subscriber_delete": [],
        "subscription_create": [],
        "subscription_patch": [],
        "subscription_list": [],
        "subscription_delete": [],
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
    """Fixture to create the mock GoogleHealthApi client with subscriber/subscription endpoints."""

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

    async def patch_subscriber_handler(
        request: aiohttp.web.Request,
    ) -> aiohttp.web.Response:
        body = await request.json()
        requests.append(
            {
                "method": "PATCH",
                "url": str(request.url),
                "body": body,
                "query": dict(request.query),
            }
        )
        return aiohttp.web.json_response(api_responses["subscriber_patch"].pop(0))

    async def list_subscribers_handler(
        request: aiohttp.web.Request,
    ) -> aiohttp.web.Response:
        requests.append(
            {
                "method": "GET",
                "url": str(request.url),
                "query": dict(request.query),
            }
        )
        return aiohttp.web.json_response(api_responses["subscriber_list"].pop(0))

    async def delete_subscriber_handler(
        request: aiohttp.web.Request,
    ) -> aiohttp.web.Response:
        requests.append(
            {
                "method": "DELETE",
                "url": str(request.url),
                "query": dict(request.query),
            }
        )
        return aiohttp.web.json_response(api_responses["subscriber_delete"].pop(0))

    async def create_subscription_handler(
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
        return aiohttp.web.json_response(api_responses["subscription_create"].pop(0))

    async def patch_subscription_handler(
        request: aiohttp.web.Request,
    ) -> aiohttp.web.Response:
        body = await request.json()
        requests.append(
            {
                "method": "PATCH",
                "url": str(request.url),
                "body": body,
                "query": dict(request.query),
            }
        )
        return aiohttp.web.json_response(api_responses["subscription_patch"].pop(0))

    async def list_subscriptions_handler(
        request: aiohttp.web.Request,
    ) -> aiohttp.web.Response:
        requests.append(
            {
                "method": "GET",
                "url": str(request.url),
                "query": dict(request.query),
            }
        )
        return aiohttp.web.json_response(api_responses["subscription_list"].pop(0))

    async def delete_subscription_handler(
        request: aiohttp.web.Request,
    ) -> aiohttp.web.Response:
        requests.append(
            {
                "method": "DELETE",
                "url": str(request.url),
            }
        )
        return aiohttp.web.json_response(api_responses["subscription_delete"].pop(0))

    auth = await auth_cb(
        [
            (
                "POST",
                "v4/projects/test-project/subscribers",
                create_subscriber_handler,
            ),
            (
                "PATCH",
                "v4/projects/test-project/subscribers/test-sub",
                patch_subscriber_handler,
            ),
            (
                "GET",
                "v4/projects/test-project/subscribers",
                list_subscribers_handler,
            ),
            (
                "DELETE",
                "v4/projects/test-project/subscribers/test-sub",
                delete_subscriber_handler,
            ),
            (
                "POST",
                "v4/projects/test-project/subscribers/test-sub/subscriptions",
                create_subscription_handler,
            ),
            (
                "PATCH",
                "v4/projects/test-project/subscribers/test-sub/subscriptions/test-subscription",
                patch_subscription_handler,
            ),
            (
                "GET",
                "v4/projects/test-project/subscribers/test-sub/subscriptions",
                list_subscriptions_handler,
            ),
            (
                "DELETE",
                "v4/projects/test-project/subscribers/test-sub/subscriptions/test-subscription",
                delete_subscription_handler,
            ),
        ]
    )
    yield GoogleHealthApi(auth)


async def test_create_subscriber(
    api: GoogleHealthApi,
    requests: list[dict[str, Any]],
    api_responses: dict[str, list[dict[str, Any]]],
) -> None:
    """Test creating a new subscriber endpoint."""
    mock_operation = {
        "name": "projects/test-project/operations/op-123",
        "done": False,
    }
    api_responses["subscriber_create"].append(mock_operation)

    configs = [
        SubscriberConfig(
            data_types=["steps", "heart-rate"],
            subscription_create_policy="AUTOMATIC",
        )
    ]

    result = await api.subscribers.create(
        project="test-project",
        endpoint_uri="https://example.com/webhook",
        endpoint_authorization_secret="Bearer mysecret",
        subscriber_configs=configs,
        subscriber_id="test-sub",
    )

    assert result.name == "projects/test-project/operations/op-123"
    assert not result.operation.done

    assert len(requests) == 1
    assert requests[0]["method"] == "POST"
    assert requests[0]["query"]["subscriberId"] == "test-sub"
    assert requests[0]["body"]["endpointUri"] == "https://example.com/webhook"
    assert requests[0]["body"]["endpointAuthorization"]["secret"] == "Bearer mysecret"
    assert requests[0]["body"]["subscriberConfigs"][0]["dataTypes"] == [
        "steps",
        "heart-rate",
    ]
    assert (
        requests[0]["body"]["subscriberConfigs"][0]["subscriptionCreatePolicy"]
        == "AUTOMATIC"
    )


async def test_patch_subscriber(
    api: GoogleHealthApi,
    requests: list[dict[str, Any]],
    api_responses: dict[str, list[dict[str, Any]]],
) -> None:
    """Test updating a subscriber."""
    mock_operation = {
        "name": "projects/test-project/operations/op-456",
        "done": True,
        "response": {
            "name": "projects/test-project/subscribers/test-sub",
            "endpointUri": "https://example.com/new-webhook",
        },
    }
    api_responses["subscriber_patch"].append(mock_operation)

    subscriber = Subscriber(
        endpoint_uri="https://example.com/new-webhook",
        endpoint_authorization=EndpointAuthorization(secret="Bearer newsecret"),
    )

    result = await api.subscribers.patch(
        name="projects/test-project/subscribers/test-sub",
        subscriber=subscriber,
        update_mask="endpointUri,endpointAuthorization",
    )

    assert result.name == "projects/test-project/operations/op-456"
    assert result.operation.done
    assert result.operation.response is not None
    assert (
        result.operation.response["name"]
        == "projects/test-project/subscribers/test-sub"
    )

    assert len(requests) == 1
    assert requests[0]["method"] == "PATCH"
    assert requests[0]["query"]["updateMask"] == "endpointUri,endpointAuthorization"
    assert requests[0]["body"]["endpointUri"] == "https://example.com/new-webhook"


async def test_list_subscribers(
    api: GoogleHealthApi,
    requests: list[dict[str, Any]],
    api_responses: dict[str, list[dict[str, Any]]],
) -> None:
    """Test listing subscribers under a project with pagination."""
    api_responses["subscriber_list"].append(
        {
            "subscribers": [
                {
                    "name": "projects/test-project/subscribers/test-sub",
                    "endpointUri": "https://example.com/webhook",
                    "endpointAuthorization": {"secretSet": True},
                }
            ],
            "nextPageToken": "page-2-token",
        }
    )
    api_responses["subscriber_list"].append(
        {
            "subscribers": [
                {
                    "name": "projects/test-project/subscribers/test-sub-2",
                    "endpointUri": "https://example.com/webhook-2",
                    "endpointAuthorization": {"secretSet": True},
                }
            ]
        }
    )

    result = await api.subscribers.list(project="test-project", page_size=1)
    assert len(result.subscribers) == 1
    assert result.subscribers[0].name == "projects/test-project/subscribers/test-sub"
    assert result.next_page_token == "page-2-token"

    pages = []
    async for page in result:
        pages.append(page)

    assert len(pages) == 2
    assert (
        pages[1].subscribers[0].name == "projects/test-project/subscribers/test-sub-2"
    )
    assert pages[1].next_page_token is None

    assert len(requests) == 2
    assert requests[0]["query"]["pageSize"] == "1"
    assert requests[1]["query"]["pageToken"] == "page-2-token"


async def test_delete_subscriber(
    api: GoogleHealthApi,
    requests: list[dict[str, Any]],
    api_responses: dict[str, list[dict[str, Any]]],
) -> None:
    """Test deleting a subscriber endpoint."""
    mock_operation = {
        "name": "projects/test-project/operations/op-delete",
        "done": True,
    }
    api_responses["subscriber_delete"].append(mock_operation)

    result = await api.subscribers.delete(
        name="projects/test-project/subscribers/test-sub",
        force=True,
    )

    assert result.name == "projects/test-project/operations/op-delete"
    assert result.operation.done

    assert len(requests) == 1
    assert requests[0]["method"] == "DELETE"
    assert requests[0]["query"]["force"] == "true"


async def test_create_subscription(
    api: GoogleHealthApi,
    requests: list[dict[str, Any]],
    api_responses: dict[str, list[dict[str, Any]]],
) -> None:
    """Test creating a subscription under a subscriber."""
    mock_subscription = {
        "name": "projects/test-project/subscribers/test-sub/subscriptions/sub-123",
        "user": "users/user-abc",
        "dataTypes": ["users/user-abc/dataTypes/steps"],
    }
    api_responses["subscription_create"].append(mock_subscription)

    result = await api.subscribers.subscriptions.create(
        parent_subscriber="projects/test-project/subscribers/test-sub",
        user="user-abc",
        data_types=["users/user-abc/dataTypes/steps"],
        subscription_id="sub-123",
    )

    assert result.user == "users/user-abc"
    assert (
        result.name
        == "projects/test-project/subscribers/test-sub/subscriptions/sub-123"
    )
    assert result.data_types == ["users/user-abc/dataTypes/steps"]

    assert len(requests) == 1
    assert requests[0]["method"] == "POST"
    assert requests[0]["query"]["subscriptionId"] == "sub-123"
    assert requests[0]["body"]["user"] == "users/user-abc"
    assert requests[0]["body"]["dataTypes"] == ["users/user-abc/dataTypes/steps"]


async def test_patch_subscription(
    api: GoogleHealthApi,
    requests: list[dict[str, Any]],
    api_responses: dict[str, list[dict[str, Any]]],
) -> None:
    """Test updating a subscription."""
    mock_subscription = {
        "name": "projects/test-project/subscribers/test-sub/subscriptions/test-subscription",
        "user": "users/user-abc",
        "dataTypes": [
            "users/user-abc/dataTypes/steps",
            "users/user-abc/dataTypes/sleep",
        ],
    }
    api_responses["subscription_patch"].append(mock_subscription)

    subscription = Subscription(
        user="users/user-abc",
        data_types=["users/user-abc/dataTypes/steps", "users/user-abc/dataTypes/sleep"],
    )

    result = await api.subscribers.subscriptions.patch(
        name="projects/test-project/subscribers/test-sub/subscriptions/test-subscription",
        subscription=subscription,
        update_mask="dataTypes",
    )

    assert result.user == "users/user-abc"
    assert result.data_types == [
        "users/user-abc/dataTypes/steps",
        "users/user-abc/dataTypes/sleep",
    ]

    assert len(requests) == 1
    assert requests[0]["method"] == "PATCH"
    assert requests[0]["query"]["updateMask"] == "dataTypes"
    assert requests[0]["body"]["dataTypes"] == [
        "users/user-abc/dataTypes/steps",
        "users/user-abc/dataTypes/sleep",
    ]


async def test_list_subscriptions(
    api: GoogleHealthApi,
    requests: list[dict[str, Any]],
    api_responses: dict[str, list[dict[str, Any]]],
) -> None:
    """Test listing subscriptions under a subscriber."""
    api_responses["subscription_list"].append(
        {
            "subscriptions": [
                {
                    "name": "projects/test-project/subscribers/test-sub/subscriptions/sub-1",
                    "user": "users/user-1",
                    "dataTypes": ["users/user-1/dataTypes/steps"],
                }
            ],
            "nextPageToken": "sub-page-2",
        }
    )
    api_responses["subscription_list"].append(
        {
            "subscriptions": [
                {
                    "name": "projects/test-project/subscribers/test-sub/subscriptions/sub-2",
                    "user": "users/user-2",
                    "dataTypes": ["users/user-2/dataTypes/sleep"],
                }
            ]
        }
    )

    result = await api.subscribers.subscriptions.list(
        parent_subscriber="projects/test-project/subscribers/test-sub",
        filter='user = "users/user-1"',
        page_size=1,
    )
    assert len(result.subscriptions) == 1
    assert result.next_page_token == "sub-page-2"

    pages = []
    async for page in result:
        pages.append(page)

    assert len(pages) == 2
    assert pages[1].subscriptions[0].user == "users/user-2"

    assert len(requests) == 2
    assert requests[0]["query"]["filter"] == 'user = "users/user-1"'
    assert requests[0]["query"]["pageSize"] == "1"
    assert requests[1]["query"]["pageToken"] == "sub-page-2"


async def test_delete_subscription(
    api: GoogleHealthApi,
    requests: list[dict[str, Any]],
    api_responses: dict[str, list[dict[str, Any]]],
) -> None:
    """Test deleting a subscription."""
    api_responses["subscription_delete"].append({})

    await api.subscribers.subscriptions.delete(
        name="projects/test-project/subscribers/test-sub/subscriptions/test-subscription"
    )

    assert len(requests) == 1
    assert requests[0]["method"] == "DELETE"
