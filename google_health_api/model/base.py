"""Base classes and registry structures for Google Health API data models."""

from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar

from mashumaro import DataClassDictMixin, field_options
from mashumaro.config import BaseConfig
from mashumaro.mixins.json import DataClassJSONMixin

T = TypeVar("T", bound=DataClassDictMixin)


class DataType(Generic[T]):
    """Represents a Google Health data type and carries its serialization metadata."""

    def __init__(self, key: str, field_name: str, payload_cls: type[T]) -> None:
        """Initialize the DataType registry token."""
        self.key = key  # kebab-case for endpoint (e.g. "heart-rate")
        self.field_name = field_name  # camelCase for JSON data block (e.g. "heartRate")
        self.payload_cls = payload_cls  # Python class to deserialize into


@dataclass
class Application(DataClassDictMixin):
    """Metadata about the application that recorded the metric."""

    package_name: str | None = field(
        metadata=field_options(alias="packageName"), default=None
    )

    class Config(BaseConfig):
        serialize_by_alias = True


@dataclass
class Device(DataClassDictMixin):
    """Metadata about the device that recorded the metric."""

    manufacturer: str | None = None
    model: str | None = None
    type: str | None = None
    uid: str | None = None

    class Config(BaseConfig):
        serialize_by_alias = True


@dataclass
class DataSource(DataClassDictMixin):
    """Metadata about the origin of a data point."""

    data_stream_name: str | None = field(
        metadata=field_options(alias="dataStreamName"), default=None
    )
    application: Application | None = None
    device: Device | None = None

    class Config(BaseConfig):
        serialize_by_alias = True


@dataclass
class DataPoint(Generic[T]):
    """Generic DataPoint containing typed metadata and payload."""

    data: T
    name: str | None = None
    data_source: DataSource | None = None

    @classmethod
    def from_api_dict(
        cls, data_type: DataType[T], raw_dict: dict[str, Any]
    ) -> "DataPoint[T]":
        """Deserialize a raw API dictionary into a type-safe DataPoint."""
        data_block = raw_dict.get("data", {})
        payload_dict = data_block.get(data_type.field_name)
        if payload_dict is None:
            raise ValueError(f"Missing expected data field: {data_type.field_name}")

        payload = data_type.payload_cls.from_dict(payload_dict)
        data_source_dict = raw_dict.get("dataSource")
        data_source = (
            DataSource.from_dict(data_source_dict) if data_source_dict else None
        )

        return cls(data=payload, name=raw_dict.get("name"), data_source=data_source)


@dataclass
class ReconciledDataPoint(Generic[T]):
    """Generic ReconciledDataPoint representing consolidated data points."""

    data_point: DataPoint[T]

    @classmethod
    def from_api_dict(
        cls, data_type: DataType[T], raw_dict: dict[str, Any]
    ) -> "ReconciledDataPoint[T]":
        """Deserialize a raw API dictionary into a type-safe ReconciledDataPoint."""
        data_point_dict = raw_dict.get("dataPoint")
        if data_point_dict is None:
            raise ValueError("Missing inner dataPoint field in reconciled response")
        return cls(data_point=DataPoint.from_api_dict(data_type, data_point_dict))


@dataclass
class Error(DataClassDictMixin):
    """Error details from the API response."""

    status: str | None = None
    code: int | None = None
    message: str | None = None
    details: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class ErrorResponse(DataClassJSONMixin):
    """A response message that contains an error message."""

    error: Error | None = None
