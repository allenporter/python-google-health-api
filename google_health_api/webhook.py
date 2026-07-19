"""Webhook signature verification utilities for the Google Health API."""

import datetime

import aiohttp

from .tink import WebhookKeyset

# The standard public URL for Google Health API webhook keysets.
GOOGLE_HEALTH_KEYSET_URL = "https://health.googleapis.com/health/v4/webhook/keyset"

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

    async def _get_keyset(self) -> WebhookKeyset:
        """Returns the cached keyset or fetches a new one if the refresh interval has elapsed.

        If a fetch fails, falls back to the cached keyset as long as it is within
        the max_cache_lifetime.
        """
        now = datetime.datetime.now(datetime.timezone.utc)

        needs_refresh = (
            self._cached_keyset is None
            or self._last_fetched is None
            or (now - self._last_fetched) > self._refresh_interval
        )

        if needs_refresh:
            try:
                async with self._websession.get(self._keyset_url) as response:
                    response.raise_for_status()
                    data = await response.json()
                    self._cached_keyset = WebhookKeyset.from_dict(data)
                    self._last_fetched = now
            except aiohttp.ClientError as e:
                # If we have a cached keyset that hasn't hit the hard limit, use it as a fallback.
                if self._cached_keyset and self._last_fetched:
                    if (now - self._last_fetched) <= self._max_cache_lifetime:
                        return self._cached_keyset
                raise RuntimeError(
                    "Failed to fetch Webhook Keyset and no valid cache exists."
                ) from e

        if not self._cached_keyset:
            raise RuntimeError("Keyset is not available.")

        return self._cached_keyset

    async def verify(self, signature_header: str, raw_payload: bytes) -> None:
        """Fetches the keyset (if needed) and verifies the payload signature."""
        keyset = await self._get_keyset()
        keyset.verify_signature(signature_header, raw_payload)
