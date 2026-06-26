"""Activity data models for Google Health API."""

from dataclasses import dataclass, field

from mashumaro import DataClassDictMixin, field_options
from mashumaro.config import BaseConfig

from .base import DataType


@dataclass
class ObservationTimeInterval(DataClassDictMixin):
    """Represents a time interval of an observed data point."""

    start_time: str = field(metadata=field_options(alias="startTime"))
    end_time: str = field(metadata=field_options(alias="endTime"))
    start_utc_offset: str | None = field(
        metadata=field_options(alias="startUtcOffset"), default=None
    )
    end_utc_offset: str | None = field(
        metadata=field_options(alias="endUtcOffset"), default=None
    )

    class Config(BaseConfig):
        serialize_by_alias = True


@dataclass
class Steps(DataClassDictMixin):
    """Step count record."""

    count: int
    interval: ObservationTimeInterval

    @property
    def start_time(self) -> str:
        """Return the start time of the interval."""
        return self.interval.start_time

    @property
    def end_time(self) -> str:
        """Return the end time of the interval."""
        return self.interval.end_time

    class Config(BaseConfig):
        serialize_by_alias = True


STEPS = DataType("steps", "steps", Steps, "steps.interval.start_time")


@dataclass
class Distance(DataClassDictMixin):
    """Distance traveled over an interval of time."""

    millimeters: int
    interval: ObservationTimeInterval

    @property
    def start_time(self) -> str:
        """Return the start time of the interval."""
        return self.interval.start_time

    @property
    def end_time(self) -> str:
        """Return the end time of the interval."""
        return self.interval.end_time

    class Config(BaseConfig):
        serialize_by_alias = True


DISTANCE = DataType("distance", "distance", Distance, "distance.interval.start_time")


@dataclass
class BasalEnergyBurned(DataClassDictMixin):
    """Number of calories burned due to basal metabolic rate over a period of time."""

    kcal: float
    interval: ObservationTimeInterval

    @property
    def start_time(self) -> str:
        """Return the start time of the interval."""
        return self.interval.start_time

    @property
    def end_time(self) -> str:
        """Return the end time of the interval."""
        return self.interval.end_time

    class Config(BaseConfig):
        serialize_by_alias = True


BASAL_ENERGY_BURNED = DataType(
    "basal-energy-burned",
    "basalEnergyBurned",
    BasalEnergyBurned,
    "basal_energy_burned.interval.start_time",
)
