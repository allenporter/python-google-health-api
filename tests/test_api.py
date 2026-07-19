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
    Height,
    OxygenSaturation,
    DailyOxygenSaturation,
    ObservationSampleTime,
    DailyRestingHeartRate,
    DailyRestingHeartRateMetadata,
)
from google_health_api.model.sleep import Sleep, SessionTimeInterval, SleepStage
from google_health_api.model.hydration import HydrationLog, VolumeQuantity
from google_health_api.model.heart import (
    Electrocardiogram,
    IrregularRhythmNotification,
    MedicalDeviceInfo,
    HeartBeat,
    AlertWindow,
)
from google_health_api.model.respiratory import (
    DailyRespiratoryRate,
    RespiratoryRateSleepSummary,
    RespiratoryRateSleepSummaryStatistics,
)
from google_health_api.model.fitness import (
    DailyVO2Max,
    DailyHeartRateZones,
    HeartRateZone,
)
from google_health_api.model.exercise import (
    Exercise,
    ExerciseMetadata,
    MetricsSummary,
)
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

    # Removed delete_handler since single delete endpoint is not supported by API.

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

    async def settings_patch_handler(
        request: aiohttp.web.Request,
    ) -> aiohttp.web.Response:
        body = await request.json()
        requests.append({"method": "PATCH", "url": str(request.url), "body": body})
        return aiohttp.web.json_response(patch_response.pop(0))

    auth = await auth_cb(
        [
            (
                "PATCH",
                "v4/users/{user}/settings",
                settings_patch_handler,
            ),
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
            # Single DELETE endpoint not supported by API.
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


async def test_sleep_daily_rollup_raises(
    api: GoogleHealthApi,
) -> None:
    """Test daily rollup raises error for unsupported type."""
    with pytest.raises(AttributeError):
        await api.sleep.daily_rollup(
            start_date=date(2026, 6, 22),
            end_date=date(2026, 6, 23),
        )


async def test_weight_daily_rollup(
    api: GoogleHealthApi,
    list_response: list[dict[str, Any]],
    requests: list[dict[str, Any]],
) -> None:
    """Test retrieving weight daily rollup."""
    list_response.append(
        {
            "rollupDataPoints": [
                {
                    "civilStartTime": {"date": {"year": 2026, "month": 6, "day": 22}},
                    "civilEndTime": {"date": {"year": 2026, "month": 6, "day": 23}},
                    "weight": {"weightGramsAvg": 75000.0},
                }
            ]
        }
    )

    result = await api.weight.daily_rollup(
        start_date=date(2026, 6, 22),
        end_date=date(2026, 6, 23),
    )
    assert len(result) == 1
    point = result[0]
    assert point.data.weight_grams_avg == 75000.0
    assert point.civil_start_time.date.year == 2026

    assert len(requests) == 1
    assert "weight/dataPoints:dailyRollUp" in requests[0]["url"]


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
    assert requests[0]["method"] == "POST"
    assert requests[0]["url"].endswith("/dataPoints:batchDelete")
    assert requests[0]["body"]["names"] == [
        "users/me/dataTypes/steps/dataPoints/point-to-delete"
    ]

    await api.steps.batch_delete(["id-1", "id-2"])
    assert len(requests) == 2
    assert requests[1]["method"] == "POST"
    assert requests[1]["url"].endswith("/dataPoints:batchDelete")
    assert requests[1]["body"]["names"] == [
        "users/me/dataTypes/steps/dataPoints/id-1",
        "users/me/dataTypes/steps/dataPoints/id-2",
    ]


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
    assert requests[4]["method"] == "POST"
    assert requests[4]["url"].endswith("/dataPoints:batchDelete")
    assert requests[4]["body"]["names"] == [
        "users/me/dataTypes/sleep/dataPoints/sleep-1"
    ]


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

    # Height
    fake_height_payload = {
        "name": "users/me/dataTypes/height/dataPoints/h-1",
        "height": {
            "heightMillimeters": 1780,
            "sampleTime": {"physicalTime": "2026-06-22T08:00:00Z"},
        },
    }
    list_response.append({"dataPoints": [fake_height_payload]})
    result_h = await api.height.list()
    assert len(result_h.data_points) == 1
    assert result_h.data_points[0].data.height_millimeters == 1780

    create_response.append(fake_height_payload)
    new_h = Height(
        height_millimeters=1780,
        sample_time=ObservationSampleTime(physical_time="2026-06-22T08:00:00Z"),
    )
    await api.height.create(DataPoint(data=new_h))
    assert requests[-1]["body"]["height"]["heightMillimeters"] == 1780


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


async def test_timezone_caching(
    api: GoogleHealthApi,
    get_response: list[dict[str, Any]],
    patch_response: list[dict[str, Any]],
    list_response: list[dict[str, Any]],
    requests: list[dict[str, Any]],
) -> None:
    """Test that timezone queries are cached to avoid redundant network calls."""
    # First call: populates settings, then calls dailyRollUp (2 requests)
    get_response.append({"name": "users/me/settings", "timeZone": "America/New_York"})
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
    assert len(requests) == 2
    assert "users/me/settings" in requests[0]["url"]
    assert "steps/dataPoints:dailyRollUp" in requests[1]["url"]

    # Clear requests to count from zero
    requests.clear()

    # Second call: uses cached timezone, does NOT call get_settings (1 request total)
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

    result = await api.steps.today()
    assert result is not None
    assert len(requests) == 1
    assert "steps/dataPoints:dailyRollUp" in requests[0]["url"]

    # Clear requests
    requests.clear()

    # Call update_settings: should update cache
    patch_response.append({"name": "users/me/settings", "timeZone": "Europe/London"})
    from google_health_api.model import Settings

    await api.update_settings(
        Settings(name="users/me/settings", time_zone="Europe/London")
    )
    assert len(requests) == 1
    assert "users/me/settings" in requests[0]["url"]

    # Clear requests
    requests.clear()

    # Third call: uses updated cached timezone from update_settings (1 request total)
    list_response.append(
        {
            "rollupDataPoints": [
                {
                    "civilStartTime": {"date": {"year": 2026, "month": 6, "day": 22}},
                    "civilEndTime": {"date": {"year": 2026, "month": 6, "day": 23}},
                    "steps": {"countSum": "6000"},
                }
            ]
        }
    )

    result = await api.steps.today()
    assert result is not None
    assert len(requests) == 1
    assert "steps/dataPoints:dailyRollUp" in requests[0]["url"]


async def test_bmi_list(
    api: GoogleHealthApi,
    list_response: list[dict[str, Any]],
    requests: list[dict[str, Any]],
) -> None:
    """Test that synthetic BMI list fetches weights/heights and calculates correctly."""
    # 1. Setup weight response payload (two weight data points)
    fake_weights_payload = {
        "dataPoints": [
            {
                "name": "users/me/dataTypes/weight/dataPoints/w-1",
                "weight": {
                    "weightGrams": 82400.0,
                    "sampleTime": {"physicalTime": "2026-07-18T12:00:00Z"},
                },
            },
            {
                "name": "users/me/dataTypes/weight/dataPoints/w-2",
                "weight": {
                    "weightGrams": 85000.0,
                    "sampleTime": {"physicalTime": "2026-07-19T12:00:00Z"},
                },
            },
        ]
    }

    # 2. Setup height response payload (two height data points at different times)
    fake_heights_payload = {
        "dataPoints": [
            {
                "name": "users/me/dataTypes/height/dataPoints/h-1",
                "height": {
                    "heightMillimeters": 1850,
                    "sampleTime": {"physicalTime": "2025-12-14T00:00:00Z"},
                },
            },
            {
                "name": "users/me/dataTypes/height/dataPoints/h-2",
                "height": {
                    "heightMillimeters": 1860,
                    "sampleTime": {"physicalTime": "2026-07-19T00:00:00Z"},
                },
            },
        ]
    }

    # list_response is used sequentially by the mock handler
    list_response.append(fake_weights_payload)
    list_response.append(fake_heights_payload)

    # 3. Call api.bmi.list()
    start_time = datetime(2026, 7, 18, tzinfo=timezone.utc)
    end_time = datetime(2026, 7, 20, tzinfo=timezone.utc)
    result = await api.bmi.list(start_time=start_time, end_time=end_time)

    # 4. Assert requests were made properly
    assert len(requests) == 2
    assert "weight/dataPoints" in requests[0]["url"]
    assert "height/dataPoints" in requests[1]["url"]

    # 5. Assert BMI calculations and alignments are correct
    assert len(result.data_points) == 2

    # Weight 1 (82.4 kg) matches Height 1 (1.85 m)
    # BMI = 82.4 / (1.85^2) = 24.08
    point1 = result.data_points[0]
    assert point1.name == "users/me/dataTypes/bmi/dataPoints/w-1"
    assert point1.data.bmi == 24.08
    assert point1.data.weight_grams == 82400.0
    assert point1.data.height_millimeters == 1850

    # Weight 2 (85.0 kg) matches Height 2 (1.86 m) (since 2026-07-19T12:00:00Z is after 2026-07-19T00:00:00Z)
    # BMI = 85.0 / (1.86^2) = 24.57
    point2 = result.data_points[1]
    assert point2.name == "users/me/dataTypes/bmi/dataPoints/w-2"
    assert point2.data.bmi == 24.57
    assert point2.data.weight_grams == 85000.0
    assert point2.data.height_millimeters == 1860


async def test_oxygen_saturation(
    api: GoogleHealthApi,
    list_response: list[dict[str, Any]],
    create_response: list[dict[str, Any]],
    requests: list[dict[str, Any]],
) -> None:
    """Test oxygen_saturation sub-API."""
    fake_payload = {
        "name": "users/me/dataTypes/oxygen-saturation/dataPoints/spo2-1",
        "oxygenSaturation": {
            "percentage": 98.5,
            "sampleTime": {"physicalTime": "2026-06-22T08:00:00Z"},
        },
    }
    list_response.append({"dataPoints": [fake_payload]})
    result = await api.oxygen_saturation.list()
    assert len(result.data_points) == 1
    assert result.data_points[0].data.percentage == 98.5

    create_response.append(fake_payload)
    new_point = OxygenSaturation(
        percentage=98.5,
        sample_time=ObservationSampleTime(physical_time="2026-06-22T08:00:00Z"),
    )
    await api.oxygen_saturation.create(DataPoint(data=new_point))
    assert requests[-1]["body"]["oxygenSaturation"]["percentage"] == 98.5


async def test_daily_oxygen_saturation(
    api: GoogleHealthApi,
    list_response: list[dict[str, Any]],
    create_response: list[dict[str, Any]],
    requests: list[dict[str, Any]],
) -> None:
    """Test daily_oxygen_saturation sub-API."""
    fake_payload = {
        "name": "users/me/dataTypes/daily-oxygen-saturation/dataPoints/d-spo2-1",
        "dailyOxygenSaturation": {
            "averagePercentage": 97.4,
            "lowerBoundPercentage": 95.0,
            "upperBoundPercentage": 99.0,
            "standardDeviationPercentage": 1.2,
            "date": {"year": 2026, "month": 6, "day": 22},
        },
    }
    list_response.append({"dataPoints": [fake_payload]})
    result = await api.daily_oxygen_saturation.list()
    assert len(result.data_points) == 1
    assert result.data_points[0].data.average_percentage == 97.4
    assert result.data_points[0].data.standard_deviation_percentage == 1.2

    create_response.append(fake_payload)
    new_point = DailyOxygenSaturation(
        average_percentage=97.4,
        lower_bound_percentage=95.0,
        upper_bound_percentage=99.0,
        standard_deviation_percentage=1.2,
        date=Date(year=2026, month=6, day=22),
    )
    await api.daily_oxygen_saturation.create(DataPoint(data=new_point))
    assert requests[-1]["body"]["dailyOxygenSaturation"]["averagePercentage"] == 97.4


async def test_exercise(
    api: GoogleHealthApi,
    list_response: list[dict[str, Any]],
    create_response: list[dict[str, Any]],
    requests: list[dict[str, Any]],
) -> None:
    """Test exercise sub-API."""
    fake_payload = {
        "name": "users/me/dataTypes/exercise/dataPoints/ex-1",
        "exercise": {
            "exerciseType": "WALKING",
            "displayName": "Afternoon Walk",
            "interval": {
                "startTime": "2026-06-22T08:00:00Z",
                "endTime": "2026-06-22T09:00:00Z",
            },
            "metricsSummary": {
                "activeZoneMinutes": 45,
                "distanceMillimeters": 3200000.0,
                "caloriesKcal": 210.5,
            },
            "exerciseMetadata": {
                "hasGps": True,
            },
        },
    }
    list_response.append({"dataPoints": [fake_payload]})
    result = await api.exercise.list()
    assert len(result.data_points) == 1
    assert result.data_points[0].data.exercise_type == "WALKING"
    assert result.data_points[0].data.display_name == "Afternoon Walk"
    assert result.data_points[0].data.metrics_summary.active_zone_minutes == 45
    assert result.data_points[0].data.exercise_metadata.has_gps is True

    create_response.append(fake_payload)
    new_point = Exercise(
        exercise_type="WALKING",
        display_name="Afternoon Walk",
        interval=SessionTimeInterval(
            start_time="2026-06-22T08:00:00Z",
            end_time="2026-06-22T09:00:00Z",
        ),
        metrics_summary=MetricsSummary(
            active_zone_minutes=45,
            distance_millimeters=3200000.0,
            calories_kcal=210.5,
        ),
        exercise_metadata=ExerciseMetadata(
            has_gps=True,
        ),
    )
    await api.exercise.create(DataPoint(data=new_point))
    assert requests[-1]["body"]["exercise"]["displayName"] == "Afternoon Walk"


async def test_electrocardiogram(
    api: GoogleHealthApi,
    list_response: list[dict[str, Any]],
    create_response: list[dict[str, Any]],
    requests: list[dict[str, Any]],
) -> None:
    """Test electrocardiogram sub-API."""
    fake_payload = {
        "name": "users/me/dataTypes/electrocardiogram/dataPoints/ecg-1",
        "electrocardiogram": {
            "resultClassification": "NORMAL_SINUS_RHYTHM",
            "samplingFrequencyHertz": 250,
            "millivoltsScalingFactor": 1000,
            "beatsPerMinuteAvg": "65",
            "interval": {
                "startTime": "2026-06-22T08:00:00Z",
                "endTime": "2026-06-22T08:00:00Z",
            },
            "medicalDeviceInfo": {
                "deviceModel": "Pixel Watch 2",
            },
            "waveformSamples": [10, 20, 30],
        },
    }
    list_response.append({"dataPoints": [fake_payload]})
    result = await api.electrocardiogram.list()
    assert len(result.data_points) == 1
    assert result.data_points[0].data.result_classification == "NORMAL_SINUS_RHYTHM"
    assert result.data_points[0].data.beats_per_minute_avg == 65
    assert (
        result.data_points[0].data.medical_device_info.device_model == "Pixel Watch 2"
    )

    create_response.append(fake_payload)
    new_point = Electrocardiogram(
        result_classification="NORMAL_SINUS_RHYTHM",
        sampling_frequency_hertz=250,
        millivolts_scaling_factor=1000,
        beats_per_minute_avg=65,
        interval=SessionTimeInterval(
            start_time="2026-06-22T08:00:00Z",
            end_time="2026-06-22T08:00:00Z",
        ),
        medical_device_info=MedicalDeviceInfo(
            device_model="Pixel Watch 2",
        ),
        waveform_samples=[10, 20, 30],
    )
    await api.electrocardiogram.create(DataPoint(data=new_point))
    assert (
        requests[-1]["body"]["electrocardiogram"]["resultClassification"]
        == "NORMAL_SINUS_RHYTHM"
    )


async def test_irregular_rhythm_notification(
    api: GoogleHealthApi,
    list_response: list[dict[str, Any]],
    create_response: list[dict[str, Any]],
    requests: list[dict[str, Any]],
) -> None:
    """Test irregular_rhythm_notification sub-API."""
    fake_payload = {
        "name": "users/me/dataTypes/irregular-rhythm-notification/dataPoints/irn-1",
        "irregularRhythmNotification": {
            "interval": {
                "startTime": "2026-06-22T08:00:00Z",
                "endTime": "2026-06-22T09:00:00Z",
            },
            "alertWindows": [
                {
                    "startTime": "2026-06-22T08:00:00Z",
                    "startUtcOffset": "-25200s",
                    "endTime": "2026-06-22T08:30:00Z",
                    "endUtcOffset": "-25200s",
                    "positive": True,
                    "heartBeats": [
                        {
                            "physicalTime": "2026-06-22T08:15:00Z",
                            "utcOffset": "-25200s",
                            "beatsPerMinute": 80,
                        }
                    ],
                }
            ],
            "medicalDeviceInfo": {
                "deviceModel": "Pixel Watch 2",
            },
        },
    }
    list_response.append({"dataPoints": [fake_payload]})
    result = await api.irregular_rhythm_notification.list()
    assert len(result.data_points) == 1
    assert len(result.data_points[0].data.alert_windows) == 1
    assert result.data_points[0].data.alert_windows[0].positive is True
    assert len(result.data_points[0].data.alert_windows[0].heart_beats) == 1
    assert (
        result.data_points[0].data.alert_windows[0].heart_beats[0].beats_per_minute
        == 80
    )

    create_response.append(fake_payload)
    new_point = IrregularRhythmNotification(
        interval=SessionTimeInterval(
            start_time="2026-06-22T08:00:00Z",
            end_time="2026-06-22T09:00:00Z",
        ),
        alert_windows=[
            AlertWindow(
                start_time="2026-06-22T08:00:00Z",
                start_utc_offset="-25200s",
                end_time="2026-06-22T08:30:00Z",
                end_utc_offset="-25200s",
                positive=True,
                heart_beats=[
                    HeartBeat(
                        physical_time="2026-06-22T08:15:00Z",
                        utc_offset="-25200s",
                        beats_per_minute=80,
                    )
                ],
            )
        ],
        medical_device_info=MedicalDeviceInfo(
            device_model="Pixel Watch 2",
        ),
    )
    await api.irregular_rhythm_notification.create(DataPoint(data=new_point))
    assert len(requests[-1]["body"]["irregularRhythmNotification"]["alertWindows"]) == 1


async def test_daily_respiratory_rate(
    api: GoogleHealthApi,
    list_response: list[dict[str, Any]],
    create_response: list[dict[str, Any]],
    requests: list[dict[str, Any]],
) -> None:
    """Test daily_respiratory_rate sub-API."""
    fake_payload = {
        "name": "users/me/dataTypes/daily-respiratory-rate/dataPoints/drr-1",
        "dailyRespiratoryRate": {
            "breathsPerMinute": 14.5,
            "date": {"year": 2026, "month": 6, "day": 22},
        },
    }
    list_response.append({"dataPoints": [fake_payload]})
    result = await api.daily_respiratory_rate.list()
    assert len(result.data_points) == 1
    assert result.data_points[0].data.breaths_per_minute == 14.5

    create_response.append(fake_payload)
    new_point = DailyRespiratoryRate(
        breaths_per_minute=14.5,
        date=Date(year=2026, month=6, day=22),
    )
    await api.daily_respiratory_rate.create(DataPoint(data=new_point))
    assert requests[-1]["body"]["dailyRespiratoryRate"]["breathsPerMinute"] == 14.5


async def test_respiratory_rate_sleep_summary(
    api: GoogleHealthApi,
    list_response: list[dict[str, Any]],
    create_response: list[dict[str, Any]],
    requests: list[dict[str, Any]],
) -> None:
    """Test respiratory_rate_sleep_summary sub-API."""
    fake_payload = {
        "name": "users/me/dataTypes/respiratory-rate-sleep-summary/dataPoints/rrss-1",
        "respiratoryRateSleepSummary": {
            "sampleTime": {
                "physicalTime": "2026-06-22T08:00:00Z",
                "utcOffset": "-25200s",
            },
            "fullSleepStats": {
                "breathsPerMinute": 15.2,
                "standardDeviation": 1.1,
                "signalToNoise": 2.5,
            },
        },
    }
    list_response.append({"dataPoints": [fake_payload]})
    result = await api.respiratory_rate_sleep_summary.list()
    assert len(result.data_points) == 1
    assert result.data_points[0].data.full_sleep_stats.breaths_per_minute == 15.2
    assert result.data_points[0].data.full_sleep_stats.standard_deviation == 1.1

    create_response.append(fake_payload)
    new_point = RespiratoryRateSleepSummary(
        sample_time=ObservationSampleTime(
            physical_time="2026-06-22T08:00:00Z",
            utc_offset="-25200s",
        ),
        full_sleep_stats=RespiratoryRateSleepSummaryStatistics(
            breaths_per_minute=15.2,
            standard_deviation=1.1,
            signal_to_noise=2.5,
        ),
    )
    await api.respiratory_rate_sleep_summary.create(DataPoint(data=new_point))
    assert (
        requests[-1]["body"]["respiratoryRateSleepSummary"]["fullSleepStats"][
            "breathsPerMinute"
        ]
        == 15.2
    )


async def test_daily_vo2_max(
    api: GoogleHealthApi,
    list_response: list[dict[str, Any]],
    create_response: list[dict[str, Any]],
    requests: list[dict[str, Any]],
) -> None:
    """Test daily_vo2_max sub-API."""
    fake_payload = {
        "name": "users/me/dataTypes/daily-vo2-max/dataPoints/dvm-1",
        "dailyVo2Max": {
            "vo2Max": 45.5,
            "date": {"year": 2026, "month": 6, "day": 22},
            "estimated": False,
            "cardioFitnessLevel": "GOOD",
            "vo2MaxCovariance": 0.5,
        },
    }
    list_response.append({"dataPoints": [fake_payload]})
    result = await api.daily_vo2_max.list()
    assert len(result.data_points) == 1
    assert result.data_points[0].data.vo2_max == 45.5
    assert result.data_points[0].data.cardio_fitness_level == "GOOD"

    create_response.append(fake_payload)
    new_point = DailyVO2Max(
        vo2_max=45.5,
        date=Date(year=2026, month=6, day=22),
        estimated=False,
        cardio_fitness_level="GOOD",
        vo2_max_covariance=0.5,
    )
    await api.daily_vo2_max.create(DataPoint(data=new_point))
    assert requests[-1]["body"]["dailyVo2Max"]["vo2Max"] == 45.5


async def test_daily_heart_rate_zones(
    api: GoogleHealthApi,
    list_response: list[dict[str, Any]],
    create_response: list[dict[str, Any]],
    requests: list[dict[str, Any]],
) -> None:
    """Test daily_heart_rate_zones sub-API."""
    fake_payload = {
        "name": "users/me/dataTypes/daily-heart-rate-zones/dataPoints/dhrz-1",
        "dailyHeartRateZones": {
            "date": {"year": 2026, "month": 6, "day": 22},
            "heartRateZones": [
                {
                    "heartRateZoneType": "LIGHT",
                    "minBeatsPerMinute": "90",
                    "maxBeatsPerMinute": "110",
                }
            ],
        },
    }
    list_response.append({"dataPoints": [fake_payload]})
    result = await api.daily_heart_rate_zones.list()
    assert len(result.data_points) == 1
    assert len(result.data_points[0].data.heart_rate_zones) == 1
    assert (
        result.data_points[0].data.heart_rate_zones[0].heart_rate_zone_type == "LIGHT"
    )
    assert result.data_points[0].data.heart_rate_zones[0].min_beats_per_minute == 90

    create_response.append(fake_payload)
    new_point = DailyHeartRateZones(
        date=Date(year=2026, month=6, day=22),
        heart_rate_zones=[
            HeartRateZone(
                heart_rate_zone_type="LIGHT",
                min_beats_per_minute=90,
                max_beats_per_minute=110,
            )
        ],
    )
    await api.daily_heart_rate_zones.create(DataPoint(data=new_point))
    assert len(requests[-1]["body"]["dailyHeartRateZones"]["heartRateZones"]) == 1
