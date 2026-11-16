"""Base classes and registry structures for Google Health API data models."""

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any, TypeVar

if TYPE_CHECKING:
    from .sleep import CivilDateTime

from mashumaro import DataClassDictMixin, field_options
from mashumaro.config import BaseConfig
from mashumaro.mixins.json import DataClassJSONMixin
from mashumaro.types import SerializationStrategy

T = TypeVar("T", bound=DataClassDictMixin)

_DURATION_RE = re.compile(r"(-?)(\d+)(?:\.(\d{1,9}))?s")


class ProtobufDurationStrategy(SerializationStrategy):
    """Mashumaro serialization strategy for google.protobuf.Duration JSON strings."""

    def serialize(self, value: timedelta) -> str:
        """Serialize a timedelta into canonical protobuf Duration JSON format."""
        total_us = (
            value.days * 86_400 + value.seconds
        ) * 1_000_000 + value.microseconds
        sign = "-" if total_us < 0 else ""
        secs, micros = divmod(abs(total_us), 1_000_000)
        if micros == 0:
            return f"{sign}{secs}s"
        if micros % 1000 == 0:
            return f"{sign}{secs}.{micros // 1000:03d}s"
        return f"{sign}{secs}.{micros:06d}s"

    def deserialize(self, value: Any) -> timedelta:
        """Deserialize a protobuf Duration JSON string (e.g. '3600s') into a timedelta."""
        if (
            not isinstance(value, str)
            or (match := _DURATION_RE.fullmatch(value)) is None
        ):
            raise ValueError(f"Invalid protobuf duration: {value!r}")
        sign_str, sec_str, frac_str = match.groups()
        seconds = int(sec_str)
        microseconds = 0
        if frac_str:
            nanos = int(frac_str.ljust(9, "0"))
            microseconds = nanos // 1000
        delta = timedelta(seconds=seconds, microseconds=microseconds)
        return -delta if sign_str == "-" else delta


class ProtobufTimestampStrategy(SerializationStrategy):
    """Mashumaro serialization strategy for google.protobuf.Timestamp RFC 3339 strings."""

    def serialize(self, value: datetime) -> str:
        """Serialize a timezone-aware datetime into canonical Z-normalized RFC 3339 format."""
        if value.tzinfo is None:
            raise ValueError(f"Protobuf timestamp must be timezone-aware: {value!r}")
        utc_val = value.astimezone(UTC)
        prefix = utc_val.strftime("%Y-%m-%dT%H:%M:%S")
        if utc_val.microsecond == 0:
            return f"{prefix}Z"
        if utc_val.microsecond % 1000 == 0:
            return f"{prefix}.{utc_val.microsecond // 1000:03d}Z"
        return f"{prefix}.{utc_val.microsecond:06d}Z"

    def deserialize(self, value: Any) -> datetime:
        """Deserialize an RFC 3339 protobuf Timestamp string into a UTC datetime."""
        if not isinstance(value, str) or (
            "T" not in value and "t" not in value and " " not in value
        ):
            raise ValueError(f"Invalid protobuf timestamp: {value!r}")
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            raise ValueError(f"Protobuf timestamp missing timezone offset: {value!r}")
        return dt.astimezone(UTC)


_SERIALIZATION_STRATEGY: dict[Any, Any] = {
    timedelta: ProtobufDurationStrategy(),
    datetime: ProtobufTimestampStrategy(),
}


class ModelConfig(BaseConfig):
    """Shared Mashumaro configuration for Google Health API models."""

    serialize_by_alias = True
    serialization_strategy = _SERIALIZATION_STRATEGY


class DataType[T: DataClassDictMixin]:
    """Represents a Google Health data type and carries its serialization metadata."""

    def __init__(
        self,
        key: str,
        field_name: str,
        payload_cls: type[T] | None,
        time_field_path: str,
        rollup_cls: type[Any] | None = None,
        read_scopes: list[str] | None = None,
        write_scopes: list[str] | None = None,
    ) -> None:
        """Initialize the DataType registry token."""
        self.key = key  # kebab-case for endpoint (e.g. "heart-rate")
        self.field_name = field_name  # camelCase for JSON data block (e.g. "heartRate")
        self.payload_cls = payload_cls  # Python class to deserialize into
        self.time_field_path = time_field_path
        self.rollup_cls = rollup_cls
        self.read_scopes = read_scopes or []
        self.write_scopes = write_scopes or []

    def __repr__(self) -> str:
        """Return the representation of DataType."""
        return f"<DataType: {self.key}>"


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

    form_factor: str | None = field(
        metadata=field_options(alias="formFactor"), default=None
    )
    display_name: str | None = field(
        metadata=field_options(alias="displayName"), default=None
    )
    manufacturer: str | None = None

    class Config(BaseConfig):
        serialize_by_alias = True


@dataclass
class DataSource(DataClassDictMixin):
    """Metadata about the origin of a data point."""

    device: Device | None = None
    platform: str | None = None
    application: Application | None = None
    recording_method: str | None = field(
        metadata=field_options(alias="recordingMethod"), default=None
    )

    class Config(BaseConfig):
        serialize_by_alias = True


@dataclass
class DataPoint[T: DataClassDictMixin]:
    """Generic DataPoint containing typed metadata and payload."""

    data: T
    name: str | None = None
    data_source: DataSource | None = None

    @classmethod
    def from_api_dict(
        cls, data_type: DataType[T], raw_dict: dict[str, Any]
    ) -> "DataPoint[T]":
        """Deserialize a raw API dictionary into a type-safe DataPoint."""
        if data_type.payload_cls is None:
            raise TypeError(f"DataType {data_type.key} does not support data points.")

        payload_dict = raw_dict.get(data_type.field_name)
        if payload_dict is None:
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
class ReconciledDataPoint[T: DataClassDictMixin]:
    """Generic ReconciledDataPoint representing consolidated data points."""

    data_point: DataPoint[T]

    @classmethod
    def from_api_dict(
        cls, data_type: DataType[T], raw_dict: dict[str, Any]
    ) -> "ReconciledDataPoint[T]":
        """Deserialize a raw API dictionary into a type-safe ReconciledDataPoint."""
        data_point_dict = raw_dict.get("dataPoint", raw_dict)
        if "name" not in data_point_dict and "dataPointName" in raw_dict:
            data_point_dict = dict(data_point_dict)
            data_point_dict["name"] = raw_dict["dataPointName"]
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


R = TypeVar("R", bound=DataClassDictMixin)


@dataclass
class DailyRollupDataPoint[R: DataClassDictMixin]:
    """Generic DailyRollupDataPoint representing consolidated rollup data points."""

    data: R
    civil_start_time: "CivilDateTime | None"
    civil_end_time: "CivilDateTime | None"

    @classmethod
    def from_api_dict(
        cls, rollup_cls: type[R], field_name: str, raw_dict: dict[str, Any]
    ) -> "DailyRollupDataPoint[R]":
        """Deserialize a raw API dictionary into a type-safe DailyRollupDataPoint."""
        payload_dict = raw_dict.get(field_name)
        if payload_dict is None:
            # Fall back to checking other dict keys (excluding civil times) to support rollups
            # with fields named differently from standard endpoints (e.g. heartRateVariabilityPersonalRange)
            for k, v in raw_dict.items():
                if k not in ("civilStartTime", "civilEndTime") and isinstance(v, dict):
                    payload_dict = v
                    break

        if payload_dict is None:
            raise ValueError(f"Missing expected rollup data field: {field_name}")

        payload = rollup_cls.from_dict(payload_dict)

        # Import here to avoid circular dependencies
        from .sleep import CivilDateTime  # noqa: PLC0415

        civil_start_dict = raw_dict.get("civilStartTime")
        civil_end_dict = raw_dict.get("civilEndTime")

        civil_start = (
            CivilDateTime.from_dict(civil_start_dict) if civil_start_dict else None
        )
        civil_end = CivilDateTime.from_dict(civil_end_dict) if civil_end_dict else None

        return cls(
            data=payload,
            civil_start_time=civil_start,
            civil_end_time=civil_end,
        )
