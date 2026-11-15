"""Tests for Google Health API data model registry and base types."""

import pytest

from google_health_api import model
from google_health_api.model import DATATYPES
from google_health_api.model.base import DataPoint


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
    assert sleep.start_time == "2026-08-03T01:00:00Z"
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
    assert completed_sleep.end_time == "2026-08-03T07:00:00Z"
    assert completed_sleep.is_in_progress is False
