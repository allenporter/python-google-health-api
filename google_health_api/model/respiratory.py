"""Respiratory data models for Google Health API."""

from dataclasses import dataclass, field

from mashumaro import DataClassDictMixin, field_options
from mashumaro.config import BaseConfig

from ..const import HealthApiScope
from .base import DataType
from .health_metric import ObservationSampleTime
from .profile import Date


@dataclass
class DailyRespiratoryRate(DataClassDictMixin):
    """A daily average respiratory rate."""

    date: Date
    breaths_per_minute: float = field(metadata=field_options(alias="breathsPerMinute"))

    class Config(BaseConfig):
        serialize_by_alias = True


@dataclass
class RespiratoryRateSleepSummaryStatistics(DataClassDictMixin):
    """Respiratory rate statistics for a given sleep stage."""

    breaths_per_minute: float = field(metadata=field_options(alias="breathsPerMinute"))
    standard_deviation: float | None = field(
        metadata=field_options(alias="standardDeviation"), default=None
    )
    signal_to_noise: float | None = field(
        metadata=field_options(alias="signalToNoise"), default=None
    )

    class Config(BaseConfig):
        serialize_by_alias = True


@dataclass
class RespiratoryRateSleepSummary(DataClassDictMixin):
    """Records respiratory rate details during sleep."""

    full_sleep_stats: RespiratoryRateSleepSummaryStatistics = field(
        metadata=field_options(alias="fullSleepStats")
    )
    sample_time: ObservationSampleTime = field(
        metadata=field_options(alias="sampleTime")
    )
    rem_sleep_stats: RespiratoryRateSleepSummaryStatistics | None = field(
        metadata=field_options(alias="remSleepStats"), default=None
    )
    deep_sleep_stats: RespiratoryRateSleepSummaryStatistics | None = field(
        metadata=field_options(alias="deepSleepStats"), default=None
    )
    light_sleep_stats: RespiratoryRateSleepSummaryStatistics | None = field(
        metadata=field_options(alias="lightSleepStats"), default=None
    )

    @property
    def start_time(self) -> str:
        """Return the sample time of the observation."""
        return self.sample_time.physical_time

    class Config(BaseConfig):
        serialize_by_alias = True


DAILY_RESPIRATORY_RATE = DataType(
    "daily-respiratory-rate",
    "dailyRespiratoryRate",
    DailyRespiratoryRate,
    "daily_respiratory_rate.date",
    read_scopes=[HealthApiScope.MEASUREMENTS_READ],
    write_scopes=[HealthApiScope.MEASUREMENTS_WRITE],
)

RESPIRATORY_RATE_SLEEP_SUMMARY = DataType(
    "respiratory-rate-sleep-summary",
    "respiratoryRateSleepSummary",
    RespiratoryRateSleepSummary,
    "respiratory_rate_sleep_summary.sample_time.physical_time",
    read_scopes=[HealthApiScope.MEASUREMENTS_READ],
    write_scopes=[HealthApiScope.MEASUREMENTS_WRITE],
)
