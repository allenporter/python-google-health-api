"""Exercise data models for Google Health API."""

from dataclasses import dataclass, field

from mashumaro import DataClassDictMixin, field_options
from mashumaro.config import BaseConfig

from ..const import HealthApiScope
from .base import DataType
from .sleep import SessionTimeInterval


@dataclass
class ExerciseMetadata(DataClassDictMixin):
    """Additional exercise metadata."""

    pool_length_millimeters: int | None = field(
        metadata=field_options(alias="poolLengthMillimeters"), default=None
    )
    has_gps: bool | None = field(metadata=field_options(alias="hasGps"), default=None)

    class Config(BaseConfig):
        serialize_by_alias = True


@dataclass
class TimeInHeartRateZones(DataClassDictMixin):
    """Time spent in each heart rate zone."""

    light_time: str | None = field(
        metadata=field_options(alias="lightTime"), default=None
    )
    moderate_time: str | None = field(
        metadata=field_options(alias="moderateTime"), default=None
    )
    vigorous_time: str | None = field(
        metadata=field_options(alias="vigorousTime"), default=None
    )
    peak_time: str | None = field(
        metadata=field_options(alias="peakTime"), default=None
    )

    class Config(BaseConfig):
        serialize_by_alias = True


@dataclass
class MobilityMetrics(DataClassDictMixin):
    """Mobility workouts specific metrics."""

    avg_ground_contact_time_duration: str | None = field(
        metadata=field_options(alias="avgGroundContactTimeDuration"), default=None
    )
    avg_vertical_ratio: float | None = field(
        metadata=field_options(alias="avgVerticalRatio"), default=None
    )
    avg_cadence_steps_per_minute: float | None = field(
        metadata=field_options(alias="avgCadenceStepsPerMinute"), default=None
    )
    avg_stride_length_millimeters: int | None = field(
        metadata=field_options(alias="avgStrideLengthMillimeters"), default=None
    )
    avg_vertical_oscillation_millimeters: int | None = field(
        metadata=field_options(alias="avgVerticalOscillationMillimeters"), default=None
    )

    class Config(BaseConfig):
        serialize_by_alias = True


@dataclass
class MetricsSummary(DataClassDictMixin):
    """Summary metrics for an exercise."""

    active_zone_minutes: int | None = field(
        metadata=field_options(alias="activeZoneMinutes"), default=None
    )
    average_heart_rate_beats_per_minute: int | None = field(
        metadata=field_options(alias="averageHeartRateBeatsPerMinute"), default=None
    )
    elevation_gain_millimeters: float | None = field(
        metadata=field_options(alias="elevationGainMillimeters"), default=None
    )
    total_swim_lengths: float | None = field(
        metadata=field_options(alias="totalSwimLengths"), default=None
    )
    average_pace_seconds_per_meter: float | None = field(
        metadata=field_options(alias="averagePaceSecondsPerMeter"), default=None
    )
    distance_millimeters: float | None = field(
        metadata=field_options(alias="distanceMillimeters"), default=None
    )
    steps: int | None = field(default=None)
    calories_kcal: float | None = field(
        metadata=field_options(alias="caloriesKcal"), default=None
    )
    average_speed_millimeters_per_second: float | None = field(
        metadata=field_options(alias="averageSpeedMillimetersPerSecond"), default=None
    )
    run_vo2_max: float | None = field(
        metadata=field_options(alias="runVo2Max"), default=None
    )
    mobility_metrics: MobilityMetrics | None = field(
        metadata=field_options(alias="mobilityMetrics"), default=None
    )
    heart_rate_zone_durations: TimeInHeartRateZones | None = field(
        metadata=field_options(alias="heartRateZoneDurations"), default=None
    )

    class Config(BaseConfig):
        serialize_by_alias = True


@dataclass
class ExerciseEvent(DataClassDictMixin):
    """Represents instantaneous events that happen during an exercise."""

    event_time: str = field(metadata=field_options(alias="eventTime"))
    event_utc_offset: str = field(metadata=field_options(alias="eventUtcOffset"))
    exercise_event_type: str = field(metadata=field_options(alias="exerciseEventType"))

    class Config(BaseConfig):
        serialize_by_alias = True


@dataclass
class SplitSummary(DataClassDictMixin):
    """Represents splits or laps recorded within an exercise."""

    split_type: str = field(metadata=field_options(alias="splitType"))
    end_utc_offset: str = field(metadata=field_options(alias="endUtcOffset"))
    start_time: str = field(metadata=field_options(alias="startTime"))
    start_utc_offset: str = field(metadata=field_options(alias="startUtcOffset"))
    end_time: str = field(metadata=field_options(alias="endTime"))
    metrics_summary: MetricsSummary = field(
        metadata=field_options(alias="metricsSummary")
    )
    active_duration: str | None = field(
        metadata=field_options(alias="activeDuration"), default=None
    )

    class Config(BaseConfig):
        serialize_by_alias = True


@dataclass
class Exercise(DataClassDictMixin):
    """An exercise that stores information about a physical activity."""

    interval: SessionTimeInterval
    exercise_type: str = field(metadata=field_options(alias="exerciseType"))
    display_name: str = field(metadata=field_options(alias="displayName"))
    metrics_summary: MetricsSummary = field(
        metadata=field_options(alias="metricsSummary")
    )
    splits: list[SplitSummary] = field(default_factory=list)
    exercise_events: list[ExerciseEvent] = field(
        metadata=field_options(alias="exerciseEvents"), default_factory=list
    )
    split_summaries: list[SplitSummary] = field(
        metadata=field_options(alias="splitSummaries"), default_factory=list
    )
    exercise_metadata: ExerciseMetadata | None = field(
        metadata=field_options(alias="exerciseMetadata"), default=None
    )
    active_duration: str | None = field(
        metadata=field_options(alias="activeDuration"), default=None
    )
    notes: str | None = field(default=None)

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


EXERCISE = DataType(
    "exercise",
    "exercise",
    Exercise,
    "exercise.interval.civil_start_time",
    read_scopes=[HealthApiScope.ACTIVITY_READ],
    write_scopes=[HealthApiScope.ACTIVITY_WRITE],
)
