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

import datetime
from dataclasses import dataclass, field
from typing import Any, Literal

import aiohttp
from mashumaro import DataClassDictMixin, field_options
from mashumaro.config import BaseConfig

from google_health_api.exceptions import HealthApiException
from google_health_api.model import DATATYPES
from google_health_api.model.base import DataType
from google_health_api.tink import WebhookKeyset

# The standard public URL for Google Health API webhook keysets.
GOOGLE_HEALTH_KEYSET_URL = (
    "https://www.gstatic.com/googlehealthapi/webhooks/webhooks_public_keyset.json"
)

# Keysets are cached in memory to avoid HTTP calls on every webhook payload.
# A refresh is attempted periodically (once per day) to gracefully rotate keys.
DEFAULT_REFRESH_INTERVAL = datetime.timedelta(days=1)

# If fetching a new keyset fails (e.g., due to a network outage), it is
# generally safe to continue using the previously cached keyset up to a maximum limit
# to ensure high availability for incoming webhooks.
DEFAULT_MAX_CACHE_LIFETIME = datetime.timedelta(days=7)


class WebhookVerifier:
    """A long-lived verifier that fetches, caches, and uses a Tink WebhookKeyset."""

    def __init__(
        self,
        websession: aiohttp.ClientSession,
        keyset_url: str = GOOGLE_HEALTH_KEYSET_URL,
        refresh_interval: datetime.timedelta = DEFAULT_REFRESH_INTERVAL,
        max_cache_lifetime: datetime.timedelta = DEFAULT_MAX_CACHE_LIFETIME,
    ) -> None:
        self._websession = websession
        self._keyset_url = keyset_url
        self._refresh_interval = refresh_interval
        self._max_cache_lifetime = max_cache_lifetime

        self._cached_keyset: WebhookKeyset | None = None
        self._last_fetched: datetime.datetime | None = None

    async def _fetch_keyset_data(self) -> dict:
        """Fetches the raw JSON keyset dictionary from the network.

        Raises:
            HealthApiException: If the network request fails.
        """
        try:
            async with self._websession.get(self._keyset_url) as response:
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientError as e:
            raise HealthApiException(
                "Failed to fetch Webhook Keyset from network."
            ) from e

    def _should_refresh(self, now: datetime.datetime) -> bool:
        """Determines if the keyset cache has expired its standard refresh interval.

        Returns True if the cache is empty, or if the time since the last fetch
        exceeds the configured refresh interval (default 24 hours).
        """
        if self._cached_keyset is None or self._last_fetched is None:
            return True
        return (now - self._last_fetched) > self._refresh_interval

    def _can_use_cache(self, now: datetime.datetime) -> bool:
        """Determines if a stale cache can still be used as a fallback.

        Returns True if the cache is present and the time since the last fetch
        is within the absolute maximum cache lifetime (default 7 days). This
        enables the API client to continue verifying payloads during extended
        Google Health API keyset URL outages.
        """
        if self._cached_keyset is None or self._last_fetched is None:
            return False
        return (now - self._last_fetched) <= self._max_cache_lifetime

    async def _get_keyset(self) -> WebhookKeyset:
        """Returns the cached keyset or fetches a new one if the refresh interval has elapsed.

        If a fetch fails, falls back to the cached keyset as long as it is within
        the max_cache_lifetime.
        """
        now = datetime.datetime.now(datetime.timezone.utc)
        if self._should_refresh(now):
            try:
                data = await self._fetch_keyset_data()
                self._cached_keyset = WebhookKeyset.from_dict(data)
                self._last_fetched = now
            except HealthApiException:
                if not self._can_use_cache(now):
                    raise
        if not self._cached_keyset:
            raise HealthApiException("Keyset is not available.")
        return self._cached_keyset

    async def verify(self, signature_header: str, raw_payload: bytes) -> None:
        """Fetches the keyset (if needed) and verifies the payload signature.

        Callers are responsible for extracting the signature from the incoming
        HTTP request headers (expected in the `GOOGLE-HEALTH-API-SIGNATURE` header)
        and providing the raw bytes of the HTTP request body. It is critical to
        pass the unmodified raw bytes; do not parse or decode the payload first.

        Args:
            signature_header: The Base64-encoded signature extracted from the
                request header.
            raw_payload: The unmodified raw HTTP request body bytes.

        Raises:
            HealthApiException: If the keyset cannot be fetched from the network
                and no valid cache exists.
            google_health_api.tink.SignatureVerificationError: If the signature
                header is malformed or the signature verification fails.
            google_health_api.tink.KeysetError: If the signature corresponds to
                an unknown or disabled key in the keyset.
            ImportError: If the `cryptography` package is not installed.
        """
        keyset = await self._get_keyset()
        keyset.verify_signature(signature_header, raw_payload)


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
