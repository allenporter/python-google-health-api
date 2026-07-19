"""Webhook models and helper mapping for Google Health API."""

from dataclasses import dataclass, field
from typing import Any

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
    type: str | None = None

    class Config(BaseConfig):
        serialize_by_alias = True
