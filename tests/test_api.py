"""Tests for Google Health library API."""

from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from typing import Any
import aiohttp
import pytest
from google_health_api.api import GoogleHealthApi
from google_health_api.model import DataPoint, DataSource
from google_health_api.model.activity import ObservationTimeInterval, Steps
from .conftest import AuthCallback


FAKE_STEPS_PAYLOAD = {
    "name": "users/me/dataTypes/steps/dataPoints/point-1",
    "dataSource": {
        "platform": "FITBIT",
        "recordingMethod": "PASSIVELY_MEASURED",
    },
    "steps": {
        "count": "500",
        "interval": {
            "startTime": "2026-06-22T08:00:00Z",
            "endTime": "2026-06-22T08:15:00Z",
        },
    },
}

FAKE_HEART_RATE_PAYLOAD = {
    "name": "users/me/dataTypes/heart-rate/dataPoints/point-2",
    "dataSource": {
        "platform": "FITBIT",
        "recordingMethod": "PASSIVELY_MEASURED",
    },
    "heartRate": {
        "beatsPerMinute": "76",
        "sampleTime": {
            "physicalTime": "2026-06-22T08:00:00Z",
        },
    },
}


@pytest.fixture(name="list_response")
def mock_list_response() -> list[dict[str, Any]]:
    """Fixture for mock list responses."""
    return []


@pytest.fixture(name="get_response")
def mock_get_response() -> list[dict[str, Any]]:
    """Fixture for mock get responses."""
    return []


@pytest.fixture(name="create_response")
def mock_create_response() -> list[dict[str, Any]]:
    """Fixture for mock create responses."""
    return []


@pytest.fixture(name="patch_response")
def mock_patch_response() -> list[dict[str, Any]]:
    """Fixture for mock patch responses."""
    return []


@pytest.fixture(name="requests")
def mock_requests() -> list[dict[str, Any]]:
    """Fixture for capturing requests."""
    return []


@pytest.fixture(name="api")
async def mock_api(
    auth_cb: AuthCallback,
    requests: list[dict[str, Any]],
    list_response: list[dict[str, Any]],
    get_response: list[dict[str, Any]],
    create_response: list[dict[str, Any]],
    patch_response: list[dict[str, Any]],
) -> AsyncGenerator[GoogleHealthApi, None]:
    """Fixture to create the mock GoogleHealthApi client."""

    async def list_handler(request: aiohttp.web.Request) -> aiohttp.web.Response:
        requests.append(
            {"method": "GET", "url": str(request.url), "query": dict(request.query)}
        )
        return aiohttp.web.json_response(list_response.pop(0))

    async def reconcile_handler(request: aiohttp.web.Request) -> aiohttp.web.Response:
        requests.append(
            {"method": "GET", "url": str(request.url), "query": dict(request.query)}
        )
        return aiohttp.web.json_response(list_response.pop(0))

    async def get_handler(request: aiohttp.web.Request) -> aiohttp.web.Response:
        requests.append({"method": "GET", "url": str(request.url)})
        return aiohttp.web.json_response(get_response.pop(0))

    async def create_handler(request: aiohttp.web.Request) -> aiohttp.web.Response:
        body = await request.json()
        requests.append({"method": "POST", "url": str(request.url), "body": body})
        return aiohttp.web.json_response(create_response.pop(0))

    async def patch_handler(request: aiohttp.web.Request) -> aiohttp.web.Response:
        body = await request.json()
        requests.append({"method": "PATCH", "url": str(request.url), "body": body})
        return aiohttp.web.json_response(patch_response.pop(0))

    async def delete_handler(request: aiohttp.web.Request) -> aiohttp.web.Response:
        requests.append({"method": "DELETE", "url": str(request.url)})
        return aiohttp.web.Response(status=204)

    async def batch_delete_handler(
        request: aiohttp.web.Request,
    ) -> aiohttp.web.Response:
        body = await request.json()
        print(f"\nDEBUG: batch_delete_handler path={request.path} url={request.url}")
        requests.append({"method": "POST", "url": str(request.url), "body": body})
        return aiohttp.web.Response(status=200)

    auth = await auth_cb(
        [
            ("GET", "v4/users/{user}/dataTypes/{dataType}/dataPoints", list_handler),
            ("POST", "v4/users/{user}/dataTypes/{dataType}/dataPoints", create_handler),
            (
                "GET",
                "v4/users/{user}/dataTypes/{dataType}/dataPoints:reconcile",
                reconcile_handler,
            ),
            (
                "GET",
                "v4/users/{user}/dataTypes/{dataType}/dataPoints/{dataPointId}",
                get_handler,
            ),
            (
                "PATCH",
                "v4/users/{user}/dataTypes/{dataType}/dataPoints/{dataPointId}",
                patch_handler,
            ),
            (
                "DELETE",
                "v4/users/{user}/dataTypes/{dataType}/dataPoints/{dataPointId}",
                delete_handler,
            ),
            (
                "POST",
                "v4/users/{user}/dataTypes/{dataType}/dataPoints:batchDelete",
                batch_delete_handler,
            ),
        ]
    )
    yield GoogleHealthApi(auth)


# ==========================================
# Steps Tests
# ==========================================


async def test_list_steps(
    api: GoogleHealthApi,
    list_response: list[dict[str, Any]],
    requests: list[dict[str, Any]],
) -> None:
    """Test listing steps with and without date filtering."""
    list_response.append(
        {"dataPoints": [FAKE_STEPS_PAYLOAD], "nextPageToken": "token-xyz"}
    )

    start = datetime(2026, 6, 22, 8, 0, 0, tzinfo=timezone.utc)
    end = datetime(2026, 6, 22, 9, 0, 0, tzinfo=timezone.utc)

    result = await api.steps.list(start_time=start, end_time=end, page_size=50)
    assert len(result.data_points) == 1
    assert result.next_page_token == "token-xyz"

    point = result.data_points[0]
    assert point.name == "users/me/dataTypes/steps/dataPoints/point-1"
    assert point.data.count == 500
    assert point.data.start_time == "2026-06-22T08:00:00Z"
    assert point.data.end_time == "2026-06-22T08:15:00Z"
    assert point.data_source is not None
    assert point.data_source.platform == "FITBIT"

    # Verify query params and AIP-160 filter
    assert len(requests) == 1
    req = requests[0]
    assert req["query"]["pageSize"] == "50"
    assert (
        req["query"]["filter"]
        == 'steps.interval.start_time >= "2026-06-22T08:00:00Z" AND steps.interval.start_time < "2026-06-22T09:00:00Z"'
    )


async def test_reconcile_steps(
    api: GoogleHealthApi,
    list_response: list[dict[str, Any]],
    requests: list[dict[str, Any]],
) -> None:
    """Test reconciling steps stream."""
    list_response.append({"reconciledDataPoints": [{"dataPoint": FAKE_STEPS_PAYLOAD}]})

    result = await api.steps.reconcile()
    assert len(result.reconciled_data_points) == 1
    point = result.reconciled_data_points[0].data_point
    assert point.data.count == 500

    assert len(requests) == 1
    assert requests[0]["method"] == "GET"
    assert "dataPoints:reconcile" in requests[0]["url"]


async def test_get_steps(
    api: GoogleHealthApi,
    get_response: list[dict[str, Any]],
    requests: list[dict[str, Any]],
) -> None:
    """Test getting individual step data point."""
    get_response.append(FAKE_STEPS_PAYLOAD)

    point = await api.steps.get("point-1")
    assert point.data.count == 500
    assert len(requests) == 1
    assert requests[0]["method"] == "GET"
    assert requests[0]["url"].endswith("/dataPoints/point-1")


async def test_create_steps(
    api: GoogleHealthApi,
    create_response: list[dict[str, Any]],
    requests: list[dict[str, Any]],
) -> None:
    """Test creating steps record."""
    create_response.append(FAKE_STEPS_PAYLOAD)

    steps_data = Steps(
        count=150,
        interval=ObservationTimeInterval(
            start_time="2026-06-22T10:00:00Z", end_time="2026-06-22T10:15:00Z"
        ),
    )
    new_point = DataPoint(
        name="users/me/dataTypes/steps/dataPoints/new-point",
        data=steps_data,
        data_source=DataSource(platform="GOOGLE_WEB_API", recording_method="MANUAL"),
    )

    point = await api.steps.create(new_point)
    assert point.data.count == 500

    assert len(requests) == 1
    req = requests[0]
    assert req["method"] == "POST"
    assert req["body"]["name"] == "users/me/dataTypes/steps/dataPoints/new-point"
    assert req["body"]["steps"]["count"] == 150
    assert req["body"]["dataSource"]["platform"] == "GOOGLE_WEB_API"


# ==========================================
# Heart Rate Tests
# ==========================================


async def test_list_heart_rate(
    api: GoogleHealthApi,
    list_response: list[dict[str, Any]],
    requests: list[dict[str, Any]],
) -> None:
    """Test listing heart rate data."""
    list_response.append({"dataPoints": [FAKE_HEART_RATE_PAYLOAD]})

    result = await api.heart_rate.list()
    assert len(result.data_points) == 1
    point = result.data_points[0]
    assert point.data.bpm == 76

    assert len(requests) == 1
    assert requests[0]["method"] == "GET"
    assert "heart-rate" in requests[0]["url"]


# ==========================================
# Deletions Tests
# ==========================================


async def test_delete_and_batch_delete(
    api: GoogleHealthApi,
    requests: list[dict[str, Any]],
) -> None:
    """Test deleting single and batch deletion of data points."""
    await api.steps.delete("point-to-delete")
    assert len(requests) == 1
    assert requests[0]["method"] == "DELETE"
    assert requests[0]["url"].endswith("/dataPoints/point-to-delete")

    await api.steps.batch_delete(["id-1", "id-2"])
    assert len(requests) == 2
    assert requests[1]["method"] == "POST"
    assert requests[1]["url"].endswith("/dataPoints:batchDelete")
    assert requests[1]["body"]["dataPointIds"] == ["id-1", "id-2"]


async def test_create_steps_without_name(
    api: GoogleHealthApi,
    create_response: list[dict[str, Any]],
    requests: list[dict[str, Any]],
) -> None:
    """Test creating steps record without a pre-specified name."""
    create_response.append(FAKE_STEPS_PAYLOAD)

    steps_data = Steps(
        count=150,
        interval=ObservationTimeInterval(
            start_time="2026-06-22T10:00:00Z", end_time="2026-06-22T10:15:00Z"
        ),
    )
    new_point = DataPoint(
        data=steps_data,
        data_source=DataSource(platform="GOOGLE_WEB_API", recording_method="MANUAL"),
    )

    point = await api.steps.create(new_point)
    assert point.data.count == 500
    assert point.name == "users/me/dataTypes/steps/dataPoints/point-1"

    assert len(requests) == 1
    req = requests[0]
    assert req["method"] == "POST"
    assert "name" not in req["body"]
    assert req["body"]["steps"]["count"] == 150
    assert req["body"]["dataSource"]["platform"] == "GOOGLE_WEB_API"


async def test_list_steps_timezone_conversion(
    api: GoogleHealthApi,
    list_response: list[dict[str, Any]],
    requests: list[dict[str, Any]],
) -> None:
    """Test listing steps with timezone conversion to UTC."""
    list_response.append({"dataPoints": [FAKE_STEPS_PAYLOAD]})

    from datetime import timezone as dt_timezone, timedelta

    est = dt_timezone(timedelta(hours=-5))
    start = datetime(2026, 6, 22, 3, 0, 0, tzinfo=est)  # 08:00:00Z
    end = datetime(2026, 6, 22, 4, 0, 0, tzinfo=est)  # 09:00:00Z

    await api.steps.list(start_time=start, end_time=end)

    assert len(requests) == 1
    req = requests[0]
    assert (
        req["query"]["filter"]
        == 'steps.interval.start_time >= "2026-06-22T08:00:00Z" AND steps.interval.start_time < "2026-06-22T09:00:00Z"'
    )
