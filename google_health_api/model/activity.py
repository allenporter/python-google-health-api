"""Activity data models for Google Health API."""

from dataclasses import dataclass, field

from mashumaro import DataClassDictMixin, field_options
from mashumaro.config import BaseConfig

from ..const import HealthApiScope
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


@dataclass
class StepsRollupValue(DataClassDictMixin):
    """Represents the result of the rollup of the steps data type."""

    count_sum: int = field(metadata=field_options(alias="countSum"))

    class Config(BaseConfig):
        serialize_by_alias = True


@dataclass
class DistanceRollupValue(DataClassDictMixin):
    """Result of the rollup of the user's distance."""

    millimeters_sum: int = field(metadata=field_options(alias="millimetersSum"))

    class Config(BaseConfig):
        serialize_by_alias = True


@dataclass
class ActiveEnergyBurnedRollupValue(DataClassDictMixin):
    """Represents the result of the rollup of active energy burned."""

    kcal_sum: float = field(metadata=field_options(alias="kcalSum"))

    class Config(BaseConfig):
        serialize_by_alias = True


@dataclass
class TotalCaloriesRollupValue(DataClassDictMixin):
    """Represents the result of the rollup of the user's total calories."""

    kcal_sum: float = field(metadata=field_options(alias="kcalSum"))

    class Config(BaseConfig):
        serialize_by_alias = True


@dataclass
class ActiveEnergyBurned(DataClassDictMixin):
    """Energy burned as part of an activity, excluding the basal energy burn."""

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


@dataclass
class FloorsRollupValue(DataClassDictMixin):
    """Represents the rollup of floors count."""

    count_sum: int = field(metadata=field_options(alias="countSum"))

    @property
    def floors_sum(self) -> int:
        """Return sum of floors (compatibility helper)."""
        return self.count_sum

    class Config(BaseConfig):
        serialize_by_alias = True


@dataclass
class Floors(DataClassDictMixin):
    """Gained elevation measured in floors over a time interval."""

    count: int
    interval: ObservationTimeInterval

    @property
    def floors(self) -> int:
        """Return floors count (compatibility helper)."""
        return self.count

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


STEPS = DataType(
    "steps",
    "steps",
    Steps,
    "steps.interval.start_time",
    StepsRollupValue,
    read_scopes=[HealthApiScope.ACTIVITY_READ],
    write_scopes=[HealthApiScope.ACTIVITY_WRITE],
)


DISTANCE = DataType(
    "distance",
    "distance",
    Distance,
    "distance.interval.start_time",
    DistanceRollupValue,
    read_scopes=[HealthApiScope.ACTIVITY_READ],
    write_scopes=[HealthApiScope.ACTIVITY_WRITE],
)


BASAL_ENERGY_BURNED = DataType(
    "basal-energy-burned",
    "basalEnergyBurned",
    BasalEnergyBurned,
    "basal_energy_burned.interval.start_time",
    read_scopes=[HealthApiScope.ACTIVITY_READ],
    write_scopes=[HealthApiScope.ACTIVITY_WRITE],
)


ACTIVE_ENERGY_BURNED = DataType(
    "active-energy-burned",
    "activeEnergyBurned",
    ActiveEnergyBurned,
    "active_energy_burned.interval.start_time",
    ActiveEnergyBurnedRollupValue,
    read_scopes=[HealthApiScope.ACTIVITY_READ],
    write_scopes=[HealthApiScope.ACTIVITY_WRITE],
)


TOTAL_CALORIES = DataType(
    "total-calories",
    "totalCalories",
    None,  # Rollup only data type
    "",
    TotalCaloriesRollupValue,
    read_scopes=[HealthApiScope.ACTIVITY_READ],
)


FLOORS = DataType(
    "floors",
    "floors",
    Floors,
    "floors.interval.start_time",
    FloorsRollupValue,
    read_scopes=[HealthApiScope.ACTIVITY_READ],
    write_scopes=[HealthApiScope.ACTIVITY_WRITE],
)
