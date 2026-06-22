"""Paired Device models for Google Health API."""

from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass, field
from typing import Self

from mashumaro import DataClassDictMixin, field_options
from mashumaro.config import BaseConfig


@dataclass
class PairedDevice(DataClassDictMixin):
    """User's paired device details."""

    name: str
    mac_address: str | None = field(
        metadata=field_options(alias="macAddress"), default=None
    )
    device_type: str | None = field(
        metadata=field_options(alias="deviceType"), default=None
    )
    features: list[str] = field(default_factory=list)
    last_sync_time: str | None = field(
        metadata=field_options(alias="lastSyncTime"), default=None
    )
    battery_status: str | None = field(
        metadata=field_options(alias="batteryStatus"), default=None
    )
    battery_level: int | None = field(
        metadata=field_options(alias="batteryLevel"), default=None
    )
    device_version: str | None = field(
        metadata=field_options(alias="deviceVersion"), default=None
    )

    class Config(BaseConfig):
        serialize_by_alias = True


@dataclass
class _ListPairedDevicesModel(DataClassDictMixin):
    """Raw model representing a page of PairedDevices."""

    paired_devices: list[PairedDevice] = field(
        metadata=field_options(alias="pairedDevices"), default_factory=list
    )
    next_page_token: str | None = field(
        metadata=field_options(alias="nextPageToken"), default=None
    )

    class Config(BaseConfig):
        serialize_by_alias = True


class ListPairedDevicesResult:
    """Response containing a list of paired devices and allowing pagination."""

    def __init__(
        self,
        response: _ListPairedDevicesModel,
        get_next_page: (
            Callable[[str], Awaitable[_ListPairedDevicesModel]] | None
        ) = None,
    ) -> None:
        """Initialize pagination result."""
        self._response = response
        self._get_next_page = get_next_page

    @property
    def paired_devices(self) -> list[PairedDevice]:
        """List of paired devices on this page."""
        return self._response.paired_devices

    @property
    def next_page_token(self) -> str | None:
        """Token to retrieve the next page."""
        return self._response.next_page_token

    async def __aiter__(self) -> AsyncIterator[Self]:
        """Async iterator to traverse through pages of paired devices."""
        response = self
        while response is not None:
            yield response
            if not response.next_page_token or not self._get_next_page:
                break
            page_result = await self._get_next_page(response.next_page_token)
            response = self.__class__(page_result, self._get_next_page)
