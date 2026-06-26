"""Sleep data models for Google Health API."""

from dataclasses import dataclass, field
from mashumaro import DataClassDictMixin, field_options
from mashumaro.config import BaseConfig

from .base import DataType
from .profile import Date


@dataclass
class TimeOfDay(DataClassDictMixin):
    """Represents a time of day."""

    hours: int | None = None
    minutes: int | None = None
    seconds: int | None = None
    nanos: int | None = None

    class Config(BaseConfig):
        serialize_by_alias = True


@dataclass
class CivilDateTime(DataClassDictMixin):
    """Civil time representation similar to google.type.DateTime."""

    date: Date | None = None
    time: TimeOfDay | None = None

    class Config(BaseConfig):
        serialize_by_alias = True


@dataclass
class SessionTimeInterval(DataClassDictMixin):
    """Represents a time interval of session data point."""

    start_time: str = field(metadata=field_options(alias="startTime"))
    end_time: str = field(metadata=field_options(alias="endTime"))
    start_utc_offset: str | None = field(
        metadata=field_options(alias="startUtcOffset"), default=None
    )
    end_utc_offset: str | None = field(
        metadata=field_options(alias="endUtcOffset"), default=None
    )
    civil_start_time: CivilDateTime | None = field(
        metadata=field_options(alias="civilStartTime"), default=None
    )
    civil_end_time: CivilDateTime | None = field(
        metadata=field_options(alias="civilEndTime"), default=None
    )

    class Config(BaseConfig):
        serialize_by_alias = True


@dataclass
class OutOfBedSegment(DataClassDictMixin):
    """A time interval to represent an out-of-bed segment."""

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
class StageSummary(DataClassDictMixin):
    """Total duration and segment count for a stage."""

    type: str | None = None
    minutes: int | None = None
    count: int | None = None

    class Config(BaseConfig):
        serialize_by_alias = True


@dataclass
class SleepSummary(DataClassDictMixin):
    """Sleep summary: metrics and stages summary."""

    minutes_to_fall_asleep: int | None = field(
        metadata=field_options(alias="minutesToFallAsleep"), default=None
    )
    minutes_after_wake_up: int | None = field(
        metadata=field_options(alias="minutesAfterWakeUp"), default=None
    )
    minutes_asleep: int | None = field(
        metadata=field_options(alias="minutesAsleep"), default=None
    )
    minutes_in_sleep_period: int | None = field(
        metadata=field_options(alias="minutesInSleepPeriod"), default=None
    )
    minutes_awake: int | None = field(
        metadata=field_options(alias="minutesAwake"), default=None
    )
    stages_summary: list[StageSummary] | None = field(
        metadata=field_options(alias="stagesSummary"), default=None
    )

    class Config(BaseConfig):
        serialize_by_alias = True


@dataclass
class SleepStage(DataClassDictMixin):
    """A sleep stage segment."""

    start_time: str = field(metadata=field_options(alias="startTime"))
    end_time: str = field(metadata=field_options(alias="endTime"))
    start_utc_offset: str = field(metadata=field_options(alias="startUtcOffset"))
    end_utc_offset: str = field(metadata=field_options(alias="endUtcOffset"))
    type: str = field(metadata=field_options(alias="type"))
    create_time: str | None = field(
        metadata=field_options(alias="createTime"), default=None
    )
    update_time: str | None = field(
        metadata=field_options(alias="updateTime"), default=None
    )

    class Config(BaseConfig):
        serialize_by_alias = True


@dataclass
class SleepMetadata(DataClassDictMixin):
    """Additional information about how the sleep was processed."""

    nap: bool | None = None
    external_id: str | None = field(
        metadata=field_options(alias="externalId"), default=None
    )
    stages_status: str | None = field(
        metadata=field_options(alias="stagesStatus"), default=None
    )
    manually_edited: bool | None = field(
        metadata=field_options(alias="manuallyEdited"), default=None
    )
    processed: bool | None = None

    class Config(BaseConfig):
        serialize_by_alias = True


@dataclass
class Sleep(DataClassDictMixin):
    """A sleep session possibly including stages."""

    interval: SessionTimeInterval
    create_time: str | None = field(
        metadata=field_options(alias="createTime"), default=None
    )
    out_of_bed_segments: list[OutOfBedSegment] | None = field(
        metadata=field_options(alias="outOfBedSegments"), default=None
    )
    summary: SleepSummary | None = None
    update_time: str | None = field(
        metadata=field_options(alias="updateTime"), default=None
    )
    stages: list[SleepStage] | None = None
    type: str | None = None
    metadata: SleepMetadata | None = None

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


SLEEP = DataType("sleep", "sleep", Sleep, "sleep.interval.start_time")
