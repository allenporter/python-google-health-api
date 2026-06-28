"""Tests for Google Health library HRV APIs."""

from datetime import date, datetime, timezone
from typing import Any
import pytest
from google_health_api.api import GoogleHealthApi
from google_health_api.model.health_metric import (
    HeartRateVariability,
    DailyHeartRateVariability,
    HeartRateVariabilityPersonalRangeRollupValue,
)

# Reuse fixtures from conftest
from .conftest import AuthCallback


FAKE_HRV_PAYLOAD = {
    "name": "users/me/dataTypes/heart-rate-variability/dataPoints/point-hrv-1",
    "dataSource": {
        "platform": "FITBIT",
        "recordingMethod": "PASSIVELY_MEASURED",
    },
    "heartRateVariability": {
        "sampleTime": {
            "physicalTime": "2026-06-22T08:00:00Z",
        },
        "rootMeanSquareOfSuccessiveDifferencesMilliseconds": 45.5,
        "standardDeviationMilliseconds": 52.1,
    },
}

FAKE_DAILY_HRV_PAYLOAD = {
    "name": "users/me/dataTypes/daily-heart-rate-variability/dataPoints/point-dhrv-1",
    "dataSource": {
        "platform": "FITBIT",
        "recordingMethod": "PASSIVELY_MEASURED",
    },
    "dailyHeartRateVariability": {
        "date": {"year": 2026, "month": 6, "day": 22},
        "averageHeartRateVariabilityMilliseconds": 48.2,
        "nonRemHeartRateBeatsPerMinute": "62",
        "entropy": 3.8,
        "deepSleepRootMeanSquareOfSuccessiveDifferencesMilliseconds": 55.4,
    },
}

FAKE_HRV_ROLLUP_PAYLOAD = {
    "rollupDataPoints": [
        {
            "civilStartTime": {"date": {"year": 2026, "month": 6, "day": 22}},
            "civilEndTime": {"date": {"year": 2026, "month": 6, "day": 23}},
            "heartRateVariabilityPersonalRange": {
                "averageHeartRateVariabilityMillisecondsMin": 40.0,
                "averageHeartRateVariabilityMillisecondsMax": 55.0,
            },
        }
    ]
}


@pytest.fixture(name="list_response")
def mock_list_response() -> list[dict[str, Any]]:
    return []


@pytest.fixture(name="get_response")
def mock_get_response() -> list[dict[str, Any]]:
    return []


@pytest.fixture(name="create_response")
def mock_create_response() -> list[dict[str, Any]]:
    return []


@pytest.fixture(name="patch_response")
def mock_patch_response() -> list[dict[str, Any]]:
    return []


@pytest.fixture(name="requests")
def mock_requests() -> list[dict[str, Any]]:
    return []


@pytest.fixture(name="api")
async def mock_api(
    auth_cb: AuthCallback,
    requests: list[dict[str, Any]],
    list_response: list[dict[str, Any]],
    get_response: list[dict[str, Any]],
    create_response: list[dict[str, Any]],
    patch_response: list[dict[str, Any]],
) -> Any:
    import aiohttp

    async def list_handler(request: aiohttp.web.Request) -> aiohttp.web.Response:
        requests.append({"method": "GET", "url": str(request.url)})
        return aiohttp.web.json_response(list_response.pop(0))

    async def create_handler(request: aiohttp.web.Request) -> aiohttp.web.Response:
        body = await request.json()
        requests.append({"method": "POST", "url": str(request.url), "body": body})
        return aiohttp.web.json_response(create_response.pop(0))

    async def get_handler(request: aiohttp.web.Request) -> aiohttp.web.Response:
        requests.append({"method": "GET", "url": str(request.url)})
        return aiohttp.web.json_response(get_response.pop(0))

    async def patch_handler(request: aiohttp.web.Request) -> aiohttp.web.Response:
        body = await request.json()
        requests.append({"method": "PATCH", "url": str(request.url), "body": body})
        return aiohttp.web.json_response(patch_response.pop(0))

    async def daily_rollup_handler(
        request: aiohttp.web.Request,
    ) -> aiohttp.web.Response:
        body = await request.json()
        requests.append({"method": "POST", "url": str(request.url), "body": body})
        return aiohttp.web.json_response(list_response.pop(0))

    auth = await auth_cb(
        [
            ("GET", "v4/users/{user}/dataTypes/{dataType}/dataPoints", list_handler),
            ("POST", "v4/users/{user}/dataTypes/{dataType}/dataPoints", create_handler),
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
                "POST",
                "v4/users/{user}/dataTypes/{dataType}/dataPoints:dailyRollUp",
                daily_rollup_handler,
            ),
        ]
    )
    yield GoogleHealthApi(auth)


async def test_list_hrv(
    api: GoogleHealthApi,
    list_response: list[dict[str, Any]],
    requests: list[dict[str, Any]],
) -> None:
    """Test listing intraday Heart Rate Variability (HRV) data points."""
    list_response.append(
        {"dataPoints": [FAKE_HRV_PAYLOAD], "nextPageToken": "token-abc"}
    )

    result = await api.heart_rate_variability.list(
        start_time=datetime(2026, 6, 22, 8, 0, 0, tzinfo=timezone.utc),
        end_time=datetime(2026, 6, 22, 9, 0, 0, tzinfo=timezone.utc),
    )

    assert len(result.data_points) == 1
    point = result.data_points[0]
    assert point.name == FAKE_HRV_PAYLOAD["name"]
    assert isinstance(point.data, HeartRateVariability)
    assert point.data.root_mean_square_of_successive_differences_milliseconds == 45.5
    assert point.data.standard_deviation_milliseconds == 52.1
    assert point.data.start_time == "2026-06-22T08:00:00Z"

    assert len(requests) == 1
    assert requests[0]["method"] == "GET"
    assert "filter=" in requests[0]["url"]


async def test_list_daily_hrv(
    api: GoogleHealthApi,
    list_response: list[dict[str, Any]],
    requests: list[dict[str, Any]],
) -> None:
    """Test listing Daily Heart Rate Variability data points."""
    list_response.append(
        {"dataPoints": [FAKE_DAILY_HRV_PAYLOAD], "nextPageToken": "token-abc"}
    )

    result = await api.daily_heart_rate_variability.list()

    assert len(result.data_points) == 1
    point = result.data_points[0]
    assert point.name == FAKE_DAILY_HRV_PAYLOAD["name"]
    assert isinstance(point.data, DailyHeartRateVariability)
    assert point.data.average_heart_rate_variability_milliseconds == 48.2
    assert point.data.non_rem_heart_rate_beats_per_minute == 62
    assert point.data.entropy == 3.8
    assert (
        point.data.deep_sleep_root_mean_square_of_successive_differences_milliseconds
        == 55.4
    )
    assert point.data.start_time == "2026-06-22"

    assert len(requests) == 1
    assert requests[0]["method"] == "GET"


async def test_daily_rollup_daily_hrv(
    api: GoogleHealthApi,
    list_response: list[dict[str, Any]],
    requests: list[dict[str, Any]],
) -> None:
    """Test daily rollup for daily-heart-rate-variability."""
    list_response.append(FAKE_HRV_ROLLUP_PAYLOAD)

    rollups = await api.daily_heart_rate_variability.daily_rollup(
        start_date=date(2026, 6, 22), end_date=date(2026, 6, 23)
    )

    assert len(rollups) == 1
    rollup = rollups[0]
    assert isinstance(rollup.data, HeartRateVariabilityPersonalRangeRollupValue)
    assert rollup.data.average_heart_rate_variability_milliseconds_min == 40.0
    assert rollup.data.average_heart_rate_variability_milliseconds_max == 55.0
    assert rollup.civil_start_time.date.year == 2026
    assert rollup.civil_start_time.date.month == 6
    assert rollup.civil_start_time.date.day == 22

    assert len(requests) == 1
    assert requests[0]["method"] == "POST"
    assert "dailyRollUp" in requests[0]["url"]
