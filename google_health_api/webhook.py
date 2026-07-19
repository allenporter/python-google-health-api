"""Webhook models and helper mapping for Google Health API.

This module provides tools for receiving and parsing real-time updates from the
Google Health API Webhooks service.

## Webhook Lifecycle

The lifecycle of a webhook integration consists of three main phases:

1. **Subscriber Registration & Verification**:
   - Register a webhook destination URL (endpoint) by creating a `Subscriber` resource
     (e.g., using `GoogleHealthApi.subscribers.create_subscriber`).
   - During registration, Google Health API performs a verification handshake by sending
     two HTTP POST requests with the JSON payload `{"type": "verification"}` to your endpoint:
     - One request includes your configured `Authorization` header token; the endpoint
       must validate it and respond with HTTP `201 Created`.
     - Another request omits the `Authorization` header; the endpoint must respond with
       HTTP `401 Unauthorized` or `403 Forbidden`.
   - Once verification succeeds, the subscriber endpoint is active.

2. **User Subscription**:
   - Link users to the subscriber endpoint to receive their updates. This can be done
     automatically based on user consents (using the `AUTOMATIC` policy in the subscriber config)
     or manually by creating a `Subscription` for each user.

3. **Parsing Data Update Notifications**:
   - When a user's subscribed health data changes, Google Health API signs the payload and sends
     an HTTP POST request containing a `"data"` block.
   - The endpoint must immediately acknowledge the receipt of the notification by responding with
     HTTP `204 No Content`.
   - Your endpoint should verify the signature delivered in the `X-HEALTHAPI-SIGNATURE` header
     (an ECDSA signature of the JSON payload) using the Google Health API's public keyset.
   - Parse the JSON payload using `WebhookNotification.from_dict()`.
   - Using the parsed `healthUserId`, `dataType`, and `civilIso8601TimeInterval`, query the API
     asynchronously to retrieve the updated data.

## Example Usage

```python
from google_health_api.webhook import WebhookNotification

# 1. Parse the incoming webhook request payload:
payload_json = await request.json()
notification = WebhookNotification.from_dict(payload_json)

# 2. Check if it's a verification request:
if notification.type == "verification":
    # Validate authorization header and return 201 Created
    ...

# 3. Otherwise, process the data change notification:
elif notification.data:
    health_user_id = notification.data.health_user_id
    operation = notification.data.operation  # e.g., "UPSERT"

    # Resolve to the concrete DataType object:
    data_type_obj = notification.data.data_type  # e.g. <DataType: steps>

    # Get the civil time interval of the updated data:
    time_interval = notification.data.civil_iso8601_time_interval
    start_time = time_interval.start_time if time_interval else None

    # Fetch the new data asynchronously from the API...
```
"""

from dataclasses import dataclass, field
from typing import Any, Literal

from mashumaro import DataClassDictMixin, field_options
from mashumaro.config import BaseConfig

from google_health_api.model import DATATYPES
from google_health_api.model.base import DataType


@dataclass
class CivilIso8601TimeInterval(DataClassDictMixin):
    """Represents a civil time interval in ISO 8601 format."""

    start_time: str = field(metadata=field_options(alias="startTime"))
    end_time: str = field(metadata=field_options(alias="endTime"))

    class Config(BaseConfig):
        serialize_by_alias = True


@dataclass
class WebhookData(DataClassDictMixin):
    """The data payload of a Google Health API webhook notification."""

    client_provided_subscription_name: str | None = field(
        metadata=field_options(alias="clientProvidedSubscriptionName"), default=None
    )
    health_user_id: str | None = field(
        metadata=field_options(alias="healthUserId"), default=None
    )
    data_type_str: str | None = field(
        metadata=field_options(alias="dataType"), default=None
    )
    operation: str | None = None
    civil_iso8601_time_interval: CivilIso8601TimeInterval | None = field(
        metadata=field_options(alias="civilIso8601TimeInterval"), default=None
    )

    class Config(BaseConfig):
        serialize_by_alias = True

    @property
    def data_type(self) -> DataType[Any] | None:
        """Get the resolved DataType object for this notification."""
        if not self.data_type_str:
            return None
        return DATATYPES.get(self.data_type_str)


@dataclass
class WebhookNotification(DataClassDictMixin):
    """A Google Health API webhook notification container."""

    data: WebhookData | None = None
    type: Literal["verification"] | None = None

    class Config(BaseConfig):
        serialize_by_alias = True
