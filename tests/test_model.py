"""Tests for Google Health API data model registry, strategies, and helpers."""

from datetime import UTC, date, datetime, time, timedelta, timezone

import pytest
from mashumaro.exceptions import InvalidFieldValue

from google_health_api import model
from google_health_api.model import (
    DATATYPES,
    ActivityLevelRollupValue,
    CivilDateTime,
    Date,
    MobilityMetrics,
    SedentaryPeriodRollupValue,
    SplitSummary,
    Subscriber,
    TimeInHeartRateZoneRollupValue,
    TimeInHeartRateZones,
    TimeOfDay,
)
from google_health_api.model.base import (
    DataPoint,
    ProtobufDurationStrategy,
    ProtobufTimestampStrategy,
)


def test_datatype_mapping() -> None:
    """Test that DATATYPES resolves standard kebab-case keys to DataType objects."""
    assert DATATYPES.get("steps") is model.STEPS
    assert DATATYPES.get("weight") is model.WEIGHT
    assert DATATYPES.get("active-energy-burned") is model.ACTIVE_ENERGY_BURNED


def test_datapoint_from_api_dict_rollup_only_raises() -> None:
    """Test DataPoint.from_api_dict raises TypeError for rollup-only DataType."""
    with pytest.raises(TypeError, match="does not support data points"):
        DataPoint.from_api_dict(model.TOTAL_CALORIES, {"totalCalories": {}})


def test_sleep_in_progress() -> None:
    """Test deserialization and properties of an in-progress sleep session."""
    raw_payload = {
        "interval": {
            "startTime": "2026-08-03T01:00:00Z",
        }
    }
    sleep = model.Sleep.from_dict(raw_payload)
    assert sleep.start_time == datetime(2026, 8, 3, 1, 0, tzinfo=UTC)
    assert sleep.end_time is None
    assert sleep.is_in_progress is True

    # Completed session
    completed_payload = {
        "interval": {
            "startTime": "2026-08-02T23:00:00Z",
            "endTime": "2026-08-03T07:00:00Z",
        }
    }
    completed_sleep = model.Sleep.from_dict(completed_payload)
    assert completed_sleep.end_time == datetime(2026, 8, 3, 7, 0, tzinfo=UTC)
    assert completed_sleep.is_in_progress is False

    # Empty interval
    empty_sleep = model.Sleep()
    assert empty_sleep.start_time is None
    assert empty_sleep.end_time is None
    assert empty_sleep.is_in_progress is False


@pytest.mark.parametrize(
    ("raw", "expected_td", "expected_serialized"),
    [
        ("0s", timedelta(0), "0s"),
        ("3600s", timedelta(hours=1), "3600s"),
        ("-25200s", timedelta(hours=-7), "-25200s"),
        ("0.25s", timedelta(milliseconds=250), "0.250s"),
        ("-0.500s", timedelta(milliseconds=-500), "-0.500s"),
        ("1.0005s", timedelta(seconds=1, microseconds=500), "1.000500s"),
        ("-1.000500s", -timedelta(seconds=1, microseconds=500), "-1.000500s"),
        ("2.000001999s", timedelta(seconds=2, microseconds=1), "2.000001s"),
    ],
)
def test_protobuf_duration_strategy(
    raw: str, expected_td: timedelta, expected_serialized: str
) -> None:
    """Test ProtobufDurationStrategy deserialize and canonical serialize formatting."""
    strategy = ProtobufDurationStrategy()
    parsed = strategy.deserialize(raw)
    assert parsed == expected_td
    assert strategy.serialize(parsed) == expected_serialized


@pytest.mark.parametrize("bad_value", ["3600", "+00:00", "10ms", "", 123])
def test_protobuf_duration_strategy_invalid(bad_value: object) -> None:
    """Test ProtobufDurationStrategy rejects malformed duration values."""
    strategy = ProtobufDurationStrategy()
    with pytest.raises(ValueError, match="Invalid protobuf duration"):
        strategy.deserialize(bad_value)


@pytest.mark.parametrize(
    ("raw", "expected_dt", "expected_serialized"),
    [
        (
            "2026-06-22T08:00:00Z",
            datetime(2026, 6, 22, 8, 0, tzinfo=UTC),
            "2026-06-22T08:00:00Z",
        ),
        (
            "2026-06-22T03:00:00-05:00",
            datetime(2026, 6, 22, 8, 0, tzinfo=UTC),
            "2026-06-22T08:00:00Z",
        ),
        (
            "2026-06-22T08:00:00.25Z",
            datetime(2026, 6, 22, 8, 0, 0, 250_000, tzinfo=UTC),
            "2026-06-22T08:00:00.250Z",
        ),
        (
            "2026-06-22T08:00:00.0005Z",
            datetime(2026, 6, 22, 8, 0, 0, 500, tzinfo=UTC),
            "2026-06-22T08:00:00.000500Z",
        ),
    ],
)
def test_protobuf_timestamp_strategy(
    raw: str, expected_dt: datetime, expected_serialized: str
) -> None:
    """Test ProtobufTimestampStrategy RFC 3339 parsing and Z-normalized formatting."""
    strategy = ProtobufTimestampStrategy()
    parsed = strategy.deserialize(raw)
    assert parsed == expected_dt
    assert parsed.tzinfo == UTC
    assert strategy.serialize(parsed) == expected_serialized


def test_protobuf_timestamp_strategy_naive_and_invalid_rejected() -> None:
    """Test naive datetime serialization and invalid string deserialization rejection."""
    strategy = ProtobufTimestampStrategy()
    with pytest.raises(ValueError, match="Protobuf timestamp must be timezone-aware"):
        strategy.serialize(datetime(2026, 6, 22, 8, 0))

    with pytest.raises(ValueError, match="Protobuf timestamp missing timezone offset"):
        strategy.deserialize("2026-06-22T08:00:00")

    with pytest.raises(ValueError, match="Invalid protobuf timestamp"):
        strategy.deserialize("2026-06-22")

    with pytest.raises(ValueError, match="Invalid protobuf timestamp"):
        strategy.deserialize(12345)


def test_rollup_and_exercise_duration_models() -> None:
    """Test rollup and exercise models deserialize/serialize durations as timedelta."""
    sedentary = SedentaryPeriodRollupValue.from_dict({"durationSum": "5400s"})
    assert sedentary.duration_sum == timedelta(minutes=90)
    assert sedentary.to_dict() == {"durationSum": "5400s"}

    activity_rollup = ActivityLevelRollupValue.from_dict(
        {
            "activityLevelRollupsByActivityLevelType": [
                {"activityLevelType": "SEDENTARY", "totalDuration": "3600s"},
                {"activityLevelType": "MODERATELY_ACTIVE", "totalDuration": "1800s"},
            ]
        }
    )
    assert len(activity_rollup.activity_level_rollups_by_activity_level_type) == 2
    assert activity_rollup.activity_level_rollups_by_activity_level_type[
        0
    ].total_duration == timedelta(hours=1)

    hr_zone_rollup = TimeInHeartRateZoneRollupValue.from_dict(
        {
            "timeInHeartRateZones": [
                {"heartRateZone": "VIGOROUS", "duration": "900s"},
            ]
        }
    )
    assert hr_zone_rollup.time_in_heart_rate_zones[0].duration == timedelta(minutes=15)

    zones = TimeInHeartRateZones.from_dict(
        {
            "lightTime": "600s",
            "moderateTime": "1200s",
            "vigorousTime": "300s",
            "peakTime": "60s",
        }
    )
    assert zones.light_time == timedelta(minutes=10)
    assert zones.moderate_time == timedelta(minutes=20)
    assert zones.vigorous_time == timedelta(minutes=5)
    assert zones.peak_time == timedelta(minutes=1)

    mobility = MobilityMetrics.from_dict({"avgGroundContactTimeDuration": "0.245s"})
    assert mobility.avg_ground_contact_time_duration == timedelta(milliseconds=245)
    assert mobility.to_dict()["avgGroundContactTimeDuration"] == "0.245s"

    split = SplitSummary.from_dict(
        {
            "startTime": "2026-06-22T08:00:00Z",
            "endTime": "2026-06-22T08:05:00Z",
            "startUtcOffset": "-25200s",
            "endUtcOffset": "-25200s",
            "activeDuration": "295s",
            "splitType": "MANUAL",
            "metricsSummary": {},
        }
    )
    assert split.start_time == datetime(2026, 6, 22, 8, 0, tzinfo=UTC)
    assert split.start_utc_offset == timedelta(hours=-7)
    assert split.active_duration == timedelta(seconds=295)

    subscriber = Subscriber.from_dict(
        {
            "name": "projects/p/subscribers/s",
            "endpointUri": "https://example.com/webhook",
            "endpointAuthorization": {"secretSet": True},
            "createTime": "2026-06-22T08:00:00Z",
            "updateTime": "2026-06-22T09:30:00Z",
        }
    )
    assert subscriber.create_time == datetime(2026, 6, 22, 8, 0, tzinfo=UTC)
    assert subscriber.update_time == datetime(2026, 6, 22, 9, 30, tzinfo=UTC)

    with pytest.raises(InvalidFieldValue):
        SedentaryPeriodRollupValue.from_dict({"durationSum": "not-a-duration"})


def test_date_time_and_civil_datetime_helpers() -> None:
    """Test stdlib conversion helpers on Date, TimeOfDay, and CivilDateTime."""
    # Date
    d = Date.from_date(date(2026, 6, 22))
    assert d == Date(year=2026, month=6, day=22)
    assert d.to_date() == date(2026, 6, 22)
    assert Date(year=2026, month=6, day=None).to_date() is None
    assert Date(year=0, month=6, day=22).to_date() is None
    assert Date(year=2026, month=6, day=0).to_date() is None

    # TimeOfDay
    tod = TimeOfDay.from_time(time(14, 30, 15, 250_000))
    assert tod == TimeOfDay(hours=14, minutes=30, seconds=15, nanos=250_000_000)
    assert tod.to_time() == time(14, 30, 15, 250_000)
    assert TimeOfDay(hours=8).to_time() == time(8, 0, 0)
    assert TimeOfDay().to_time() == time(0, 0, 0)

    # CivilDateTime from/to date
    civil_date_only = CivilDateTime.from_date(date(2026, 6, 22))
    assert civil_date_only.to_date() == date(2026, 6, 22)
    assert civil_date_only.to_datetime() == datetime(2026, 6, 22, 0, 0)
    assert civil_date_only.to_datetime(tzinfo=UTC) == datetime(
        2026, 6, 22, 0, 0, tzinfo=UTC
    )

    # CivilDateTime from/to datetime
    tz_minus_5 = timezone(timedelta(hours=-5))
    civil_dt = CivilDateTime.from_datetime(
        datetime(2026, 6, 22, 14, 30, 15, 500, tzinfo=tz_minus_5)
    )
    assert civil_dt.to_date() == date(2026, 6, 22)
    assert civil_dt.to_datetime() == datetime(2026, 6, 22, 14, 30, 15, 500)
    assert civil_dt.to_datetime(tzinfo=tz_minus_5) == datetime(
        2026, 6, 22, 14, 30, 15, 500, tzinfo=tz_minus_5
    )

    # Partial/empty CivilDateTime
    assert CivilDateTime().to_date() is None
    assert CivilDateTime().to_datetime() is None
