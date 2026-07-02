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


@dataclass
class Altitude(DataClassDictMixin):
    """Altitude gain delta measurement."""

    interval: ObservationTimeInterval
    gain_millimeters: int = field(metadata=field_options(alias="gainMillimeters"))

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
class AltitudeRollupValue(DataClassDictMixin):
    """Represents the result of the rollup of the user's altitude."""

    gain_millimeters_sum: int | None = field(
        metadata=field_options(alias="gainMillimetersSum"), default=None
    )

    class Config(BaseConfig):
        serialize_by_alias = True


ALTITUDE = DataType(
    "altitude",
    "altitude",
    Altitude,
    "altitude.interval.start_time",
    AltitudeRollupValue,
    read_scopes=[HealthApiScope.ACTIVITY_READ],
    write_scopes=[HealthApiScope.ACTIVITY_WRITE],
)


@dataclass
class ActiveMinutesByActivityLevel(DataClassDictMixin):
    """Active minutes by activity level."""

    activity_level: str = field(metadata=field_options(alias="activityLevel"))
    active_minutes: int = field(metadata=field_options(alias="activeMinutes"))

    class Config(BaseConfig):
        serialize_by_alias = True


@dataclass
class ActiveMinutes(DataClassDictMixin):
    """Record of active minutes in a given time interval."""

    interval: ObservationTimeInterval
    active_minutes_by_activity_level: list[ActiveMinutesByActivityLevel] = field(
        metadata=field_options(alias="activeMinutesByActivityLevel"),
        default_factory=list,
    )

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
class ActiveMinutesRollupByActivityLevel(DataClassDictMixin):
    """Active minutes rollup details for an activity level."""

    activity_level: str | None = field(
        metadata=field_options(alias="activityLevel"), default=None
    )
    active_minutes_sum: int | None = field(
        metadata=field_options(alias="activeMinutesSum"), default=None
    )

    class Config(BaseConfig):
        serialize_by_alias = True


@dataclass
class ActiveMinutesRollupValue(DataClassDictMixin):
    """Represents the result of the rollup of the active minutes data type."""

    active_minutes_rollup_by_activity_level: list[
        ActiveMinutesRollupByActivityLevel
    ] = field(
        metadata=field_options(alias="activeMinutesRollupByActivityLevel"),
        default_factory=list,
    )

    class Config(BaseConfig):
        serialize_by_alias = True


ACTIVE_MINUTES = DataType(
    "active-minutes",
    "activeMinutes",
    ActiveMinutes,
    "active_minutes.interval.start_time",
    ActiveMinutesRollupValue,
    read_scopes=[HealthApiScope.ACTIVITY_READ],
    write_scopes=[HealthApiScope.ACTIVITY_WRITE],
)


@dataclass
class ActiveZoneMinutes(DataClassDictMixin):
    """Record of active zone minutes in a given time interval."""

    interval: ObservationTimeInterval
    heart_rate_zone: str = field(metadata=field_options(alias="heartRateZone"))
    active_zone_minutes: int = field(metadata=field_options(alias="activeZoneMinutes"))

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
class ActiveZoneMinutesRollupValue(DataClassDictMixin):
    """Represents the result of the rollup of the active zone minutes data type."""

    sum_in_cardio_heart_zone: int | None = field(
        metadata=field_options(alias="sumInCardioHeartZone"), default=None
    )
    sum_in_fat_burn_heart_zone: int | None = field(
        metadata=field_options(alias="sumInFatBurnHeartZone"), default=None
    )
    sum_in_peak_heart_zone: int | None = field(
        metadata=field_options(alias="sumInPeakHeartZone"), default=None
    )

    class Config(BaseConfig):
        serialize_by_alias = True


ACTIVE_ZONE_MINUTES = DataType(
    "active-zone-minutes",
    "activeZoneMinutes",
    ActiveZoneMinutes,
    "active_zone_minutes.interval.start_time",
    ActiveZoneMinutesRollupValue,
    read_scopes=[HealthApiScope.ACTIVITY_READ],
    write_scopes=[HealthApiScope.ACTIVITY_WRITE],
)


@dataclass
class SedentaryPeriod(DataClassDictMixin):
    """Represents the periods of time that the user was sedentary."""

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
class SedentaryPeriodRollupValue(DataClassDictMixin):
    """Represents the result of the rollup of the user's sedentary periods."""

    duration_sum: str | None = field(
        metadata=field_options(alias="durationSum"), default=None
    )

    class Config(BaseConfig):
        serialize_by_alias = True


SEDENTARY_PERIOD = DataType(
    "sedentary-period",
    "sedentaryPeriod",
    SedentaryPeriod,
    "sedentary_period.interval.start_time",
    SedentaryPeriodRollupValue,
    read_scopes=[HealthApiScope.ACTIVITY_READ],
    write_scopes=[HealthApiScope.ACTIVITY_WRITE],
)


@dataclass
class SwimLengthsData(DataClassDictMixin):
    """Swim lengths data over the time interval."""

    stroke_count: int = field(metadata=field_options(alias="strokeCount"))
    interval: ObservationTimeInterval
    swim_stroke_type: str = field(metadata=field_options(alias="swimStrokeType"))

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
class SwimLengthsDataRollupValue(DataClassDictMixin):
    """Represents the result of the rollup of the swim lengths data type."""

    stroke_count_sum: int | None = field(
        metadata=field_options(alias="strokeCountSum"), default=None
    )

    class Config(BaseConfig):
        serialize_by_alias = True


SWIM_LENGTHS_DATA = DataType(
    "swim-lengths-data",
    "swimLengthsData",
    SwimLengthsData,
    "swim_lengths_data.interval.start_time",
    SwimLengthsDataRollupValue,
    read_scopes=[HealthApiScope.ACTIVITY_READ],
    write_scopes=[HealthApiScope.ACTIVITY_WRITE],
)


@dataclass
class ActivityLevel(DataClassDictMixin):
    """Activity level during a certain time interval."""

    interval: ObservationTimeInterval
    activity_level_type: str = field(metadata=field_options(alias="activityLevelType"))

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
class ActivityLevelRollupByActivityLevelType(DataClassDictMixin):
    """Total duration in a specific activity level type."""

    activity_level_type: str | None = field(
        metadata=field_options(alias="activityLevelType"), default=None
    )
    total_duration: str | None = field(
        metadata=field_options(alias="totalDuration"), default=None
    )

    class Config(BaseConfig):
        serialize_by_alias = True


@dataclass
class ActivityLevelRollupValue(DataClassDictMixin):
    """Represents the result of the rollup of the activity level data type."""

    activity_level_rollups_by_activity_level_type: list[
        ActivityLevelRollupByActivityLevelType
    ] = field(
        metadata=field_options(alias="activityLevelRollupsByActivityLevelType"),
        default_factory=list,
    )

    class Config(BaseConfig):
        serialize_by_alias = True


ACTIVITY_LEVEL = DataType(
    "activity-level",
    "activityLevel",
    ActivityLevel,
    "activity_level.interval.start_time",
    ActivityLevelRollupValue,
    read_scopes=[HealthApiScope.ACTIVITY_READ],
    write_scopes=[HealthApiScope.ACTIVITY_WRITE],
)


@dataclass
class TimeInHeartRateZone(DataClassDictMixin):
    """Time in heart rate zone record."""

    interval: ObservationTimeInterval
    heart_rate_zone_type: str = field(metadata=field_options(alias="heartRateZoneType"))

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
class TimeInHeartRateZoneValue(DataClassDictMixin):
    """Represents the total time spent in a specific heart rate zone."""

    duration: str | None = None
    heart_rate_zone: str | None = field(
        metadata=field_options(alias="heartRateZone"), default=None
    )

    class Config(BaseConfig):
        serialize_by_alias = True


@dataclass
class TimeInHeartRateZoneRollupValue(DataClassDictMixin):
    """Represents the result of the rollup of the time in heart rate zone data type."""

    time_in_heart_rate_zones: list[TimeInHeartRateZoneValue] = field(
        metadata=field_options(alias="timeInHeartRateZones"),
        default_factory=list,
    )

    class Config(BaseConfig):
        serialize_by_alias = True


TIME_IN_HEART_RATE_ZONE = DataType(
    "time-in-heart-rate-zone",
    "timeInHeartRateZone",
    TimeInHeartRateZone,
    "time_in_heart_rate_zone.interval.start_time",
    TimeInHeartRateZoneRollupValue,
    read_scopes=[HealthApiScope.ACTIVITY_READ],
    write_scopes=[HealthApiScope.ACTIVITY_WRITE],
)


@dataclass
class CaloriesInHeartRateZoneValue(DataClassDictMixin):
    """Represents the amount of kilocalories burned in a specific heart rate zone."""

    heart_rate_zone: str | None = field(
        metadata=field_options(alias="heartRateZone"), default=None
    )
    kcal: float | None = None

    class Config(BaseConfig):
        serialize_by_alias = True


@dataclass
class CaloriesInHeartRateZoneRollupValue(DataClassDictMixin):
    """Represents the result of the rollup of the calories in heart rate zone data type."""

    calories_in_heart_rate_zones: list[CaloriesInHeartRateZoneValue] = field(
        metadata=field_options(alias="caloriesInHeartRateZones"),
        default_factory=list,
    )

    class Config(BaseConfig):
        serialize_by_alias = True


CALORIES_IN_HEART_RATE_ZONE = DataType(
    "calories-in-heart-rate-zone",
    "caloriesInHeartRateZone",
    None,  # Rollup only data type
    "",
    CaloriesInHeartRateZoneRollupValue,
    read_scopes=[HealthApiScope.ACTIVITY_READ],
)
