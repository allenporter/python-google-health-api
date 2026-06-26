"""Tests for Google Health library API."""

from collections.abc import AsyncGenerator
from datetime import date, datetime, timezone
from typing import Any
import aiohttp
import pytest
from google_health_api.api import GoogleHealthApi
from google_health_api.model import DataPoint, DataSource
from google_health_api.model import Date
from google_health_api.model.activity import (
    ObservationTimeInterval,
    Steps,
    Distance,
    BasalEnergyBurned,
    Floors,
)
from google_health_api.model.health_metric import (
    VO2Max,
    Weight,
    ObservationSampleTime,
    DailyRestingHeartRate,
    DailyRestingHeartRateMetadata,
)
from google_health_api.model.sleep import Sleep, SessionTimeInterval, SleepStage
from google_health_api.model.hydration import HydrationLog, VolumeQuantity
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

    async def daily_rollup_handler(
        request: aiohttp.web.Request,
    ) -> aiohttp.web.Response:
        body = await request.json()
        requests.append({"method": "POST", "url": str(request.url), "body": body})
        return aiohttp.web.json_response(list_response.pop(0))

    async def settings_handler(request: aiohttp.web.Request) -> aiohttp.web.Response:
        requests.append({"method": "GET", "url": str(request.url)})
        return aiohttp.web.json_response(get_response.pop(0))

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
            (
                "POST",
                "v4/users/{user}/dataTypes/{dataType}/dataPoints:dailyRollUp",
                daily_rollup_handler,
            ),
            (
                "GET",
                "v4/users/{user}/settings",
                settings_handler,
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
# Daily Rollup Tests
# ==========================================


async def test_steps_daily_rollup(
    api: GoogleHealthApi,
    list_response: list[dict[str, Any]],
    requests: list[dict[str, Any]],
) -> None:
    """Test retrieving steps daily rollup."""
    list_response.append(
        {
            "rollupDataPoints": [
                {
                    "civilStartTime": {"date": {"year": 2026, "month": 6, "day": 22}},
                    "civilEndTime": {"date": {"year": 2026, "month": 6, "day": 23}},
                    "steps": {"countSum": "5000"},
                }
            ]
        }
    )

    result = await api.steps.daily_rollup(
        start_date=date(2026, 6, 22),
        end_date=date(2026, 6, 23),
    )
    assert len(result) == 1
    point = result[0]
    assert point.data.count_sum == 5000
    assert point.civil_start_time.date.year == 2026
    assert point.civil_start_time.date.month == 6
    assert point.civil_start_time.date.day == 22

    assert len(requests) == 1
    assert requests[0]["method"] == "POST"
    assert "steps/dataPoints:dailyRollUp" in requests[0]["url"]
    assert requests[0]["body"]["range"]["start"]["date"]["day"] == 22
    assert requests[0]["body"]["range"]["end"]["date"]["day"] == 23


async def test_heart_rate_daily_rollup_raises(
    api: GoogleHealthApi,
) -> None:
    """Test daily rollup raises error for unsupported type."""
    with pytest.raises(AttributeError):
        await api.heart_rate.daily_rollup(
            start_date=date(2026, 6, 22),
            end_date=date(2026, 6, 23),
        )


async def test_steps_today(
    api: GoogleHealthApi,
    list_response: list[dict[str, Any]],
    get_response: list[dict[str, Any]],
    requests: list[dict[str, Any]],
) -> None:
    """Test steps today helper."""
    # Mock settings response for timezone lookup
    get_response.append(
        {
            "name": "users/me/settings",
            "timeZone": "America/New_York",
        }
    )
    list_response.append(
        {
            "rollupDataPoints": [
                {
                    "civilStartTime": {"date": {"year": 2026, "month": 6, "day": 22}},
                    "civilEndTime": {"date": {"year": 2026, "month": 6, "day": 23}},
                    "steps": {"countSum": "8000"},
                }
            ]
        }
    )

    result = await api.steps.today()
    assert result is not None
    assert result.data.count_sum == 8000

    # Verification: 2 requests (settings GET then rollup POST)
    assert len(requests) == 2
    assert requests[0]["method"] == "GET"
    assert "users/me/settings" in requests[0]["url"]
    assert requests[1]["method"] == "POST"
    assert "steps/dataPoints:dailyRollUp" in requests[1]["url"]


async def test_steps_yesterday(
    api: GoogleHealthApi,
    list_response: list[dict[str, Any]],
    requests: list[dict[str, Any]],
) -> None:
    """Test steps yesterday helper."""
    list_response.append(
        {
            "rollupDataPoints": [
                {
                    "civilStartTime": {"date": {"year": 2026, "month": 6, "day": 21}},
                    "civilEndTime": {"date": {"year": 2026, "month": 6, "day": 22}},
                    "steps": {"countSum": "7500"},
                }
            ]
        }
    )

    # Call yesterday helper with explicit timezone to skip settings lookup
    result = await api.steps.yesterday(time_zone="America/New_York")
    assert result is not None
    assert result.data.count_sum == 7500

    # Verification: 1 request (direct rollup POST)
    assert len(requests) == 1
    assert requests[0]["method"] == "POST"
    assert "steps/dataPoints:dailyRollUp" in requests[0]["url"]


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


# ==========================================
# Sleep Tests
# ==========================================


async def test_sleep_crud(
    api: GoogleHealthApi,
    list_response: list[dict[str, Any]],
    get_response: list[dict[str, Any]],
    create_response: list[dict[str, Any]],
    patch_response: list[dict[str, Any]],
    requests: list[dict[str, Any]],
) -> None:
    """Test sleep endpoints (list, get, create, patch, delete)."""
    fake_sleep_payload = {
        "name": "users/me/dataTypes/sleep/dataPoints/sleep-1",
        "sleep": {
            "interval": {
                "startTime": "2026-06-22T22:00:00Z",
                "endTime": "2026-06-23T06:00:00Z",
            },
            "stages": [
                {
                    "startTime": "2026-06-22T22:00:00Z",
                    "endTime": "2026-06-22T23:00:00Z",
                    "startUtcOffset": "+00:00",
                    "endUtcOffset": "+00:00",
                    "type": "LIGHT",
                }
            ],
        },
    }

    # 1. List
    list_response.append({"dataPoints": [fake_sleep_payload]})
    start = datetime(2026, 6, 22, 22, 0, 0, tzinfo=timezone.utc)
    end = datetime(2026, 6, 23, 6, 0, 0, tzinfo=timezone.utc)
    result = await api.sleep.list(start_time=start, end_time=end)
    assert len(result.data_points) == 1
    assert result.data_points[0].data.start_time == "2026-06-22T22:00:00Z"
    assert len(requests) == 1
    assert (
        requests[0]["query"]["filter"]
        == 'sleep.interval.end_time >= "2026-06-22T22:00:00Z" AND sleep.interval.end_time < "2026-06-23T06:00:00Z"'
    )

    # 2. Get
    get_response.append(fake_sleep_payload)
    point = await api.sleep.get("sleep-1")
    assert point.data.end_time == "2026-06-23T06:00:00Z"
    assert len(requests) == 2

    # 3. Create
    create_response.append(fake_sleep_payload)
    new_sleep = Sleep(
        interval=SessionTimeInterval(
            start_time="2026-06-22T22:00:00Z", end_time="2026-06-23T06:00:00Z"
        ),
        stages=[
            SleepStage(
                start_time="2026-06-22T22:00:00Z",
                end_time="2026-06-22T23:00:00Z",
                start_utc_offset="+00:00",
                end_utc_offset="+00:00",
                type="LIGHT",
            )
        ],
    )
    created = await api.sleep.create(DataPoint(data=new_sleep))
    assert created.data.stages is not None
    assert created.data.stages[0].type == "LIGHT"
    assert len(requests) == 3
    assert (
        requests[2]["body"]["sleep"]["interval"]["startTime"] == "2026-06-22T22:00:00Z"
    )

    # 4. Patch
    patch_response.append(fake_sleep_payload)
    patched = await api.sleep.patch("sleep-1", DataPoint(data=new_sleep))
    assert patched.data.start_time == "2026-06-22T22:00:00Z"
    assert len(requests) == 4

    # 5. Delete
    await api.sleep.delete("sleep-1")
    assert len(requests) == 5
    assert requests[4]["method"] == "DELETE"


# ==========================================
# Distance and BasalEnergyBurned Tests
# ==========================================


async def test_distance_and_basal_energy_burned(
    api: GoogleHealthApi,
    list_response: list[dict[str, Any]],
    create_response: list[dict[str, Any]],
    requests: list[dict[str, Any]],
) -> None:
    """Test distance and basal energy burned clients."""
    # Distance
    fake_distance_payload = {
        "name": "users/me/dataTypes/distance/dataPoints/dist-1",
        "distance": {
            "millimeters": "5000",
            "interval": {
                "startTime": "2026-06-22T08:00:00Z",
                "endTime": "2026-06-22T08:15:00Z",
            },
        },
    }
    list_response.append({"dataPoints": [fake_distance_payload]})
    result_dist = await api.distance.list()
    assert len(result_dist.data_points) == 1
    assert result_dist.data_points[0].data.millimeters == 5000

    create_response.append(fake_distance_payload)
    new_dist = Distance(
        millimeters=5000,
        interval=ObservationTimeInterval(
            start_time="2026-06-22T08:00:00Z", end_time="2026-06-22T08:15:00Z"
        ),
    )
    await api.distance.create(DataPoint(data=new_dist))
    assert requests[-1]["body"]["distance"]["millimeters"] == 5000

    # Basal Energy Burned
    fake_beb_payload = {
        "name": "users/me/dataTypes/basal-energy-burned/dataPoints/beb-1",
        "basalEnergyBurned": {
            "kcal": 15.5,
            "interval": {
                "startTime": "2026-06-22T08:00:00Z",
                "endTime": "2026-06-22T08:15:00Z",
            },
        },
    }
    list_response.append({"dataPoints": [fake_beb_payload]})
    result_beb = await api.basal_energy_burned.list()
    assert len(result_beb.data_points) == 1
    assert result_beb.data_points[0].data.kcal == 15.5

    create_response.append(fake_beb_payload)
    new_beb = BasalEnergyBurned(
        kcal=15.5,
        interval=ObservationTimeInterval(
            start_time="2026-06-22T08:00:00Z", end_time="2026-06-22T08:15:00Z"
        ),
    )
    await api.basal_energy_burned.create(DataPoint(data=new_beb))
    assert requests[-1]["body"]["basalEnergyBurned"]["kcal"] == 15.5


# ==========================================
# VO2Max and Weight Tests
# ==========================================


async def test_vo2_max_and_weight(
    api: GoogleHealthApi,
    list_response: list[dict[str, Any]],
    create_response: list[dict[str, Any]],
    requests: list[dict[str, Any]],
) -> None:
    """Test VO2Max and Weight clients."""
    # VO2 Max
    fake_vo2_payload = {
        "name": "users/me/dataTypes/vo2-max/dataPoints/vo2-1",
        "vo2Max": {
            "vo2Max": 45.2,
            "measurementMethod": "FITBIT_RUN",
            "sampleTime": {"physicalTime": "2026-06-22T08:00:00Z"},
        },
    }
    list_response.append({"dataPoints": [fake_vo2_payload]})
    result_vo2 = await api.vo2_max.list()
    assert len(result_vo2.data_points) == 1
    assert result_vo2.data_points[0].data.vo2_max == 45.2

    create_response.append(fake_vo2_payload)
    new_vo2 = VO2Max(
        vo2_max=45.2,
        sample_time=ObservationSampleTime(physical_time="2026-06-22T08:00:00Z"),
        measurement_method="FITBIT_RUN",
    )
    await api.vo2_max.create(DataPoint(data=new_vo2))
    assert requests[-1]["body"]["vo2Max"]["vo2Max"] == 45.2

    # Weight
    fake_weight_payload = {
        "name": "users/me/dataTypes/weight/dataPoints/w-1",
        "weight": {
            "weightGrams": 75000.0,
            "notes": "morning weigh-in",
            "sampleTime": {"physicalTime": "2026-06-22T08:00:00Z"},
        },
    }
    list_response.append({"dataPoints": [fake_weight_payload]})
    result_w = await api.weight.list()
    assert len(result_w.data_points) == 1
    assert result_w.data_points[0].data.weight_grams == 75000.0

    create_response.append(fake_weight_payload)
    new_w = Weight(
        weight_grams=75000.0,
        sample_time=ObservationSampleTime(physical_time="2026-06-22T08:00:00Z"),
        notes="morning weigh-in",
    )
    await api.weight.create(DataPoint(data=new_w))
    assert requests[-1]["body"]["weight"]["weightGrams"] == 75000.0


# ==========================================
# Floors, HydrationLog, and Resting Heart Rate Tests
# ==========================================


async def test_floors_hydration_and_resting_hr(
    api: GoogleHealthApi,
    list_response: list[dict[str, Any]],
    create_response: list[dict[str, Any]],
    requests: list[dict[str, Any]],
) -> None:
    """Test Floors, HydrationLog, and DailyRestingHeartRate clients."""

    # Floors
    fake_floors_payload = {
        "name": "users/me/dataTypes/floors/dataPoints/fl-1",
        "floors": {
            "count": "3",
            "interval": {
                "startTime": "2026-06-22T08:00:00Z",
                "endTime": "2026-06-22T08:15:00Z",
            },
        },
    }
    list_response.append({"dataPoints": [fake_floors_payload]})
    result_fl = await api.floors.list()
    assert len(result_fl.data_points) == 1
    assert result_fl.data_points[0].data.count == 3
    assert result_fl.data_points[0].data.floors == 3

    create_response.append(fake_floors_payload)
    new_fl = Floors(
        count=3,
        interval=ObservationTimeInterval(
            start_time="2026-06-22T08:00:00Z",
            end_time="2026-06-22T08:15:00Z",
        ),
    )
    await api.floors.create(DataPoint(data=new_fl))
    assert requests[-1]["body"]["floors"]["count"] == 3

    # HydrationLog
    fake_hydration_payload = {
        "name": "users/me/dataTypes/hydration-log/dataPoints/hy-1",
        "hydrationLog": {
            "amountConsumed": {"milliliters": 250.0, "userProvidedUnit": "MILLILITER"},
            "interval": {
                "startTime": "2026-06-22T08:00:00Z",
                "endTime": "2026-06-22T08:05:00Z",
            },
        },
    }
    list_response.append({"dataPoints": [fake_hydration_payload]})
    result_hy = await api.hydration_log.list()
    assert len(result_hy.data_points) == 1
    assert result_hy.data_points[0].data.amount_consumed.milliliters == 250.0

    create_response.append(fake_hydration_payload)
    new_hy = HydrationLog(
        amount_consumed=VolumeQuantity(
            milliliters=250.0, user_provided_unit="MILLILITER"
        ),
        interval=SessionTimeInterval(
            start_time="2026-06-22T08:00:00Z",
            end_time="2026-06-22T08:05:00Z",
        ),
    )
    await api.hydration_log.create(DataPoint(data=new_hy))
    assert (
        requests[-1]["body"]["hydrationLog"]["amountConsumed"]["milliliters"] == 250.0
    )

    # DailyRestingHeartRate
    fake_resting_payload = {
        "name": "users/me/dataTypes/daily-resting-heart-rate/dataPoints/hr-1",
        "dailyRestingHeartRate": {
            "beatsPerMinute": 62,
            "date": {"year": 2026, "month": 6, "day": 22},
            "dailyRestingHeartRateMetadata": {"calculationMethod": "WITH_SLEEP"},
        },
    }
    list_response.append({"dataPoints": [fake_resting_payload]})
    result_resting = await api.daily_resting_heart_rate.list()
    assert len(result_resting.data_points) == 1
    assert result_resting.data_points[0].data.beats_per_minute == 62

    create_response.append(fake_resting_payload)
    new_resting = DailyRestingHeartRate(
        beats_per_minute=62,
        date=Date(year=2026, month=6, day=22),
        daily_resting_heart_rate_metadata=DailyRestingHeartRateMetadata(
            calculation_method="WITH_SLEEP"
        ),
    )
    await api.daily_resting_heart_rate.create(DataPoint(data=new_resting))
    assert requests[-1]["body"]["dailyRestingHeartRate"]["beatsPerMinute"] == 62
