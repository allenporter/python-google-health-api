"""Health metric data models for Google Health API."""

from dataclasses import dataclass, field

from mashumaro import DataClassDictMixin, field_options
from mashumaro.config import BaseConfig

from ..const import HealthApiScope
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


@dataclass
class HeartRateRollupValue(DataClassDictMixin):
    """Represents the result of the rollup of the heart rate data type."""

    beats_per_minute_min: float | None = field(
        metadata=field_options(alias="beatsPerMinuteMin"), default=None
    )
    beats_per_minute_avg: float | None = field(
        metadata=field_options(alias="beatsPerMinuteAvg"), default=None
    )
    beats_per_minute_max: float | None = field(
        metadata=field_options(alias="beatsPerMinuteMax"), default=None
    )

    class Config(BaseConfig):
        serialize_by_alias = True


HEART_RATE = DataType(
    "heart-rate",
    "heartRate",
    HeartRate,
    "heart_rate.sample_time.physical_time",
    HeartRateRollupValue,
    read_scopes=[HealthApiScope.MEASUREMENTS_READ],
    write_scopes=[HealthApiScope.MEASUREMENTS_WRITE],
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
    read_scopes=[HealthApiScope.MEASUREMENTS_READ],
    write_scopes=[HealthApiScope.MEASUREMENTS_WRITE],
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


@dataclass
class WeightRollupValue(DataClassDictMixin):
    """Represents the result of the rollup of the weight data type."""

    weight_grams_avg: float | None = field(
        metadata=field_options(alias="weightGramsAvg"), default=None
    )

    class Config(BaseConfig):
        serialize_by_alias = True


WEIGHT = DataType(
    "weight",
    "weight",
    Weight,
    "weight.sample_time.physical_time",
    WeightRollupValue,
    read_scopes=[HealthApiScope.MEASUREMENTS_READ],
    write_scopes=[HealthApiScope.MEASUREMENTS_WRITE],
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


@dataclass
class RestingHeartRatePersonalRangeRollupValue(DataClassDictMixin):
    """Represents the rollup value for the daily resting heart rate data type."""

    beats_per_minute_max: float | None = field(
        metadata=field_options(alias="beatsPerMinuteMax"), default=None
    )
    beats_per_minute_min: float | None = field(
        metadata=field_options(alias="beatsPerMinuteMin"), default=None
    )

    class Config(BaseConfig):
        serialize_by_alias = True


DAILY_RESTING_HEART_RATE = DataType(
    "daily-resting-heart-rate",
    "dailyRestingHeartRate",
    DailyRestingHeartRate,
    "daily_resting_heart_rate.date.year",
    RestingHeartRatePersonalRangeRollupValue,
    read_scopes=[HealthApiScope.MEASUREMENTS_READ],
    write_scopes=[HealthApiScope.MEASUREMENTS_WRITE],
)


@dataclass
class HeartRateVariability(DataClassDictMixin):
    """Heart rate variability (HRV) intraday measurement."""

    sample_time: ObservationSampleTime = field(
        metadata=field_options(alias="sampleTime")
    )
    root_mean_square_of_successive_differences_milliseconds: float | None = field(
        metadata=field_options(
            alias="rootMeanSquareOfSuccessiveDifferencesMilliseconds"
        ),
        default=None,
    )
    standard_deviation_milliseconds: float | None = field(
        metadata=field_options(alias="standardDeviationMilliseconds"),
        default=None,
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


HEART_RATE_VARIABILITY = DataType(
    "heart-rate-variability",
    "heartRateVariability",
    HeartRateVariability,
    "heart_rate_variability.sample_time.physical_time",
    read_scopes=[HealthApiScope.MEASUREMENTS_READ],
    write_scopes=[HealthApiScope.MEASUREMENTS_WRITE],
)


@dataclass
class DailyHeartRateVariability(DataClassDictMixin):
    """Daily heart rate variability measurement."""

    date: Date = field(metadata=field_options(alias="date"))
    average_heart_rate_variability_milliseconds: float | None = field(
        metadata=field_options(alias="averageHeartRateVariabilityMilliseconds"),
        default=None,
    )
    non_rem_heart_rate_beats_per_minute: int | None = field(
        metadata=field_options(alias="nonRemHeartRateBeatsPerMinute"),
        default=None,
    )
    entropy: float | None = field(default=None)
    deep_sleep_root_mean_square_of_successive_differences_milliseconds: float | None = (
        field(
            metadata=field_options(
                alias="deepSleepRootMeanSquareOfSuccessiveDifferencesMilliseconds"
            ),
            default=None,
        )
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


@dataclass
class HeartRateVariabilityPersonalRangeRollupValue(DataClassDictMixin):
    """Represents the rollup of the user's daily heart rate variability personal range."""

    average_heart_rate_variability_milliseconds_min: float | None = field(
        metadata=field_options(alias="averageHeartRateVariabilityMillisecondsMin"),
        default=None,
    )
    average_heart_rate_variability_milliseconds_max: float | None = field(
        metadata=field_options(alias="averageHeartRateVariabilityMillisecondsMax"),
        default=None,
    )

    class Config(BaseConfig):
        serialize_by_alias = True


DAILY_HEART_RATE_VARIABILITY = DataType(
    "daily-heart-rate-variability",
    "dailyHeartRateVariability",
    DailyHeartRateVariability,
    "daily_heart_rate_variability.date.year",
    HeartRateVariabilityPersonalRangeRollupValue,
    read_scopes=[HealthApiScope.MEASUREMENTS_READ],
    write_scopes=[HealthApiScope.MEASUREMENTS_WRITE],
)


@dataclass
class BloodGlucose(DataClassDictMixin):
    """Represents a blood glucose level measurement."""

    sample_time: ObservationSampleTime = field(
        metadata=field_options(alias="sampleTime")
    )
    blood_glucose_milligrams_per_deciliter: float = field(
        metadata=field_options(alias="bloodGlucoseMilligramsPerDeciliter")
    )
    measurement_source: str | None = field(
        metadata=field_options(alias="measurementSource"), default=None
    )
    notes: str | None = None
    meal_type: str | None = field(
        metadata=field_options(alias="mealType"), default=None
    )
    measurement_timing: str | None = field(
        metadata=field_options(alias="measurementTiming"), default=None
    )
    specimen: str | None = None

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


@dataclass
class BloodGlucoseRollupValue(DataClassDictMixin):
    """Represents the result of the rollup of the blood glucose data type."""

    blood_glucose_milligrams_per_deciliter_avg: float | None = field(
        metadata=field_options(alias="bloodGlucoseMilligramsPerDeciliterAvg"),
        default=None,
    )

    class Config(BaseConfig):
        serialize_by_alias = True


BLOOD_GLUCOSE = DataType(
    "blood-glucose",
    "bloodGlucose",
    BloodGlucose,
    "blood_glucose.sample_time.physical_time",
    BloodGlucoseRollupValue,
    read_scopes=[HealthApiScope.MEASUREMENTS_READ],
    write_scopes=[HealthApiScope.MEASUREMENTS_WRITE],
)


@dataclass
class CoreBodyTemperature(DataClassDictMixin):
    """Core body temperature measurement."""

    temperature_celsius: float = field(
        metadata=field_options(alias="temperatureCelsius")
    )
    sample_time: ObservationSampleTime = field(
        metadata=field_options(alias="sampleTime")
    )
    id: str | None = None
    measurement_location: str | None = field(
        metadata=field_options(alias="measurementLocation"), default=None
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


@dataclass
class CoreBodyTemperatureRollupValue(DataClassDictMixin):
    """Represents the result of the rollup of the core body temperature data type."""

    temperature_celsius_min: float | None = field(
        metadata=field_options(alias="temperatureCelsiusMin"), default=None
    )
    temperature_celsius_avg: float | None = field(
        metadata=field_options(alias="temperatureCelsiusAvg"), default=None
    )
    temperature_celsius_max: float | None = field(
        metadata=field_options(alias="temperatureCelsiusMax"), default=None
    )

    class Config(BaseConfig):
        serialize_by_alias = True


CORE_BODY_TEMPERATURE = DataType(
    "core-body-temperature",
    "coreBodyTemperature",
    CoreBodyTemperature,
    "core_body_temperature.sample_time.physical_time",
    CoreBodyTemperatureRollupValue,
    read_scopes=[HealthApiScope.MEASUREMENTS_READ],
    write_scopes=[HealthApiScope.MEASUREMENTS_WRITE],
)


@dataclass
class BodyFat(DataClassDictMixin):
    """Body fat measurement."""

    percentage: float
    sample_time: ObservationSampleTime = field(
        metadata=field_options(alias="sampleTime")
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


@dataclass
class BodyFatRollupValue(DataClassDictMixin):
    """Represents the result of the rollup of the body fat data type."""

    body_fat_percentage_avg: float | None = field(
        metadata=field_options(alias="bodyFatPercentageAvg"), default=None
    )

    class Config(BaseConfig):
        serialize_by_alias = True


BODY_FAT = DataType(
    "body-fat",
    "bodyFat",
    BodyFat,
    "body_fat.sample_time.physical_time",
    BodyFatRollupValue,
    read_scopes=[HealthApiScope.MEASUREMENTS_READ],
    write_scopes=[HealthApiScope.MEASUREMENTS_WRITE],
)


@dataclass
class RunVO2Max(DataClassDictMixin):
    """VO2 max value calculated based on the user's running activity."""

    run_vo2_max: float = field(metadata=field_options(alias="runVo2Max"))
    sample_time: ObservationSampleTime = field(
        metadata=field_options(alias="sampleTime")
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


@dataclass
class RunVO2MaxRollupValue(DataClassDictMixin):
    """Represents the result of the rollup of the user's run VO2 max."""

    rate_max: float | None = field(
        metadata=field_options(alias="rateMax"), default=None
    )
    rate_min: float | None = field(
        metadata=field_options(alias="rateMin"), default=None
    )
    rate_avg: float | None = field(
        metadata=field_options(alias="rateAvg"), default=None
    )

    class Config(BaseConfig):
        serialize_by_alias = True


RUN_VO2_MAX = DataType(
    "run-vo2-max",
    "runVo2Max",
    RunVO2Max,
    "run_vo2_max.sample_time.physical_time",
    RunVO2MaxRollupValue,
    read_scopes=[HealthApiScope.MEASUREMENTS_READ],
    write_scopes=[HealthApiScope.MEASUREMENTS_WRITE],
)
