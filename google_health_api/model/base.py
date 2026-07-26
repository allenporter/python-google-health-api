"""Base classes and registry structures for Google Health API data models."""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, TypeVar

if TYPE_CHECKING:
    from .sleep import CivilDateTime

from mashumaro import DataClassDictMixin, field_options
from mashumaro.config import BaseConfig
from mashumaro.mixins.json import DataClassJSONMixin

T = TypeVar("T", bound=DataClassDictMixin)


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
        from .sleep import CivilDateTime

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
