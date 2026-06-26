"""Health metric data models for Google Health API."""

from dataclasses import dataclass, field

from mashumaro import DataClassDictMixin, field_options
from mashumaro.config import BaseConfig

from .base import DataType


@dataclass
class ObservationSampleTime(DataClassDictMixin):
    """Represents a sample time of an observed data point."""

    physical_time: str = field(metadata=field_options(alias="physicalTime"))
    utc_offset: str | None = field(
        metadata=field_options(alias="utcOffset"), default=None
    )

    class Config(BaseConfig):
        serialize_by_alias = True


@dataclass
class HeartRateMetadata(DataClassDictMixin):
    """Heart rate metadata."""

    sensor_location: str | None = field(
        metadata=field_options(alias="sensorLocation"), default=None
    )
    motion_context: str | None = field(
        metadata=field_options(alias="motionContext"), default=None
    )

    class Config(BaseConfig):
        serialize_by_alias = True


@dataclass
class HeartRate(DataClassDictMixin):
    """Heart rate record."""

    beats_per_minute: int = field(metadata=field_options(alias="beatsPerMinute"))
    sample_time: ObservationSampleTime = field(
        metadata=field_options(alias="sampleTime")
    )
    metadata: HeartRateMetadata | None = None

    @property
    def bpm(self) -> int:
        """Return the beats per minute value (deprecated/compatibility alias)."""
        return self.beats_per_minute

    @property
    def start_time(self) -> str:
        """Return the physical time (for compatibility)."""
        return self.sample_time.physical_time

    @property
    def end_time(self) -> str:
        """Return the physical time (for compatibility)."""
        return self.sample_time.physical_time

    class Config(BaseConfig):
        serialize_by_alias = True


HEART_RATE = DataType(
    "heart-rate",
    "heartRate",
    HeartRate,
    "heart_rate.sample_time.physical_time",
)
