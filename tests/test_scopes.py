"""Tests for the OAuth scope querying and mapping properties in the SDK."""

from unittest.mock import MagicMock
import aiohttp

from google_health_api.api import GoogleHealthApi
from google_health_api.const import HealthApiScope
from tests.conftest import FakeAuth


def test_sub_api_required_scopes() -> None:
    """Test that all client sub-APIs expose the correct required read/write scopes."""
    mock_client = MagicMock(spec=aiohttp.ClientSession)
    auth = FakeAuth(mock_client)
    api = GoogleHealthApi(auth)

    # Activity Metrics
    assert api.steps.required_read_scopes == [HealthApiScope.ACTIVITY_READ]
    assert api.steps.required_write_scopes == [HealthApiScope.ACTIVITY_WRITE]
    assert api.distance.required_read_scopes == [HealthApiScope.ACTIVITY_READ]
    assert api.distance.required_write_scopes == [HealthApiScope.ACTIVITY_WRITE]

    # Health Metrics / Measurements
    assert api.heart_rate.required_read_scopes == [HealthApiScope.MEASUREMENTS_READ]
    assert api.heart_rate.required_write_scopes == [HealthApiScope.MEASUREMENTS_WRITE]
    assert api.weight.required_read_scopes == [HealthApiScope.MEASUREMENTS_READ]
    assert api.weight.required_write_scopes == [HealthApiScope.MEASUREMENTS_WRITE]
    assert api.height.required_read_scopes == [HealthApiScope.MEASUREMENTS_READ]
    assert api.height.required_write_scopes == [HealthApiScope.MEASUREMENTS_WRITE]
    assert api.oxygen_saturation.required_read_scopes == [
        HealthApiScope.MEASUREMENTS_READ
    ]
    assert api.oxygen_saturation.required_write_scopes == [
        HealthApiScope.MEASUREMENTS_WRITE
    ]
    assert api.daily_oxygen_saturation.required_read_scopes == [
        HealthApiScope.MEASUREMENTS_READ
    ]
    assert api.daily_oxygen_saturation.required_write_scopes == [
        HealthApiScope.MEASUREMENTS_WRITE
    ]
    assert api.electrocardiogram.required_read_scopes == [
        HealthApiScope.MEASUREMENTS_READ
    ]
    assert api.electrocardiogram.required_write_scopes == [
        HealthApiScope.MEASUREMENTS_WRITE
    ]
    assert api.irregular_rhythm_notification.required_read_scopes == [
        HealthApiScope.MEASUREMENTS_READ
    ]
    assert api.irregular_rhythm_notification.required_write_scopes == [
        HealthApiScope.MEASUREMENTS_WRITE
    ]

    # Sleep
    assert api.sleep.required_read_scopes == [HealthApiScope.SLEEP_READ]
    assert api.sleep.required_write_scopes == [HealthApiScope.SLEEP_WRITE]

    # Exercise
    assert api.exercise.required_read_scopes == [HealthApiScope.ACTIVITY_READ]
    assert api.exercise.required_write_scopes == [HealthApiScope.ACTIVITY_WRITE]

    # Nutrition & Hydration
    assert api.nutrition_log.required_read_scopes == [HealthApiScope.NUTRITION_READ]
    assert api.nutrition_log.required_write_scopes == [HealthApiScope.NUTRITION_WRITE]
    assert api.hydration_log.required_read_scopes == [HealthApiScope.NUTRITION_READ]
    assert api.hydration_log.required_write_scopes == [HealthApiScope.NUTRITION_WRITE]

    # Special sub-APIs
    assert api.paired_devices.required_read_scopes == [HealthApiScope.SETTINGS_READ]
    assert api.paired_devices.required_write_scopes == []

    assert api.subscribers.required_read_scopes == [
        "https://www.googleapis.com/auth/cloud-platform"
    ]
    assert api.subscribers.required_write_scopes == [
        "https://www.googleapis.com/auth/cloud-platform"
    ]

    assert api.subscribers.subscriptions.required_read_scopes == [
        "https://www.googleapis.com/auth/cloud-platform"
    ]
    assert api.subscribers.subscriptions.required_write_scopes == [
        "https://www.googleapis.com/auth/cloud-platform"
    ]
