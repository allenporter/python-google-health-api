"""Tests for Google Health API webhook parsing and mapping."""

from google_health_api import model
from google_health_api.webhook import WebhookNotification


def test_parse_verification_request() -> None:
    """Test parsing an endpoint verification request payload."""
    payload = {"type": "verification"}
    notification = WebhookNotification.from_dict(payload)
    assert notification.type == "verification"
    assert notification.data is None


def test_parse_data_notification() -> None:
    """Test parsing a real-time data update notification payload."""
    payload = {
        "data": {
            "clientProvidedSubscriptionName": "subscription-uuid-123",
            "healthUserId": "user-uuid-456",
            "dataType": "steps",
            "operation": "UPSERT",
            "civilIso8601TimeInterval": {
                "startTime": "2026-03-07T17:29:00",
                "endTime": "2026-03-07T17:34:00",
            },
        }
    }
    notification = WebhookNotification.from_dict(payload)
    assert notification.type is None
    assert notification.data is not None
    assert (
        notification.data.client_provided_subscription_name == "subscription-uuid-123"
    )
    assert notification.data.health_user_id == "user-uuid-456"
    assert notification.data.data_type_str == "steps"
    assert notification.data.operation == "UPSERT"
    assert notification.data.civil_iso8601_time_interval is not None
    assert (
        notification.data.civil_iso8601_time_interval.start_time
        == "2026-03-07T17:29:00"
    )
    assert (
        notification.data.civil_iso8601_time_interval.end_time == "2026-03-07T17:34:00"
    )

    # Verify resolution to DataType object
    assert notification.data.data_type is model.STEPS
    assert repr(notification.data.data_type) == "<DataType: steps>"
