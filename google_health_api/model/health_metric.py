"""Health metric data models for Google Health API."""

from dataclasses import dataclass, field

from mashumaro import DataClassDictMixin, field_options
from mashumaro.config import BaseConfig

from .base import DataType
from .profile import Date


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


@dataclass
class VO2Max(DataClassDictMixin):
    """VO2 max measurement."""

    vo2_max: float = field(metadata=field_options(alias="vo2Max"))
    sample_time: ObservationSampleTime = field(
        metadata=field_options(alias="sampleTime")
    )
    measurement_method: str | None = field(
        metadata=field_options(alias="measurementMethod"), default=None
    )

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


VO2_MAX = DataType(
    "vo2-max",
    "vo2Max",
    VO2Max,
    "vo2_max.sample_time.physical_time",
)


@dataclass
class Weight(DataClassDictMixin):
    """Body weight measurement."""

    weight_grams: float = field(metadata=field_options(alias="weightGrams"))
    sample_time: ObservationSampleTime = field(
        metadata=field_options(alias="sampleTime")
    )
    notes: str | None = None

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


WEIGHT = DataType(
    "weight",
    "weight",
    Weight,
    "weight.sample_time.physical_time",
)


@dataclass
class DailyRestingHeartRateMetadata(DataClassDictMixin):
    """Metadata for the daily resting heart rate."""

    calculation_method: str | None = field(
        metadata=field_options(alias="calculationMethod"), default=None
    )

    class Config(BaseConfig):
        serialize_by_alias = True


@dataclass
class DailyRestingHeartRate(DataClassDictMixin):
    """Daily resting heart rate measurement."""

    beats_per_minute: int = field(metadata=field_options(alias="beatsPerMinute"))
    date: Date = field(metadata=field_options(alias="date"))
    daily_resting_heart_rate_metadata: DailyRestingHeartRateMetadata | None = field(
        metadata=field_options(alias="dailyRestingHeartRateMetadata"), default=None
    )

    @property
    def start_time(self) -> str:
        """Return ISO format string of date."""
        return f"{self.date.year:04d}-{self.date.month:02d}-{self.date.day:02d}"

    @property
    def end_time(self) -> str:
        """Return ISO format string of date."""
        return f"{self.date.year:04d}-{self.date.month:02d}-{self.date.day:02d}"

    class Config(BaseConfig):
        serialize_by_alias = True


DAILY_RESTING_HEART_RATE = DataType(
    "daily-resting-heart-rate",
    "dailyRestingHeartRate",
    DailyRestingHeartRate,
    "daily_resting_heart_rate.date.year",
)
