"""Daily fitness data models for Google Health API."""

from dataclasses import dataclass, field

from mashumaro import DataClassDictMixin, field_options
from mashumaro.config import BaseConfig

from ..const import HealthApiScope
from .base import DataType
from .profile import Date


@dataclass
class DailyVO2Max(DataClassDictMixin):
    """Daily summary of the user's VO2 max (cardio fitness score)."""

    vo2_max: float = field(metadata=field_options(alias="vo2Max"))
    date: Date
    estimated: bool | None = field(default=None)
    cardio_fitness_level: str | None = field(
        metadata=field_options(alias="cardioFitnessLevel"), default=None
    )
    vo2_max_covariance: float | None = field(
        metadata=field_options(alias="vo2MaxCovariance"), default=None
    )

    class Config(BaseConfig):
        serialize_by_alias = True


@dataclass
class HeartRateZone(DataClassDictMixin):
    """The heart rate zone thresholds."""

    heart_rate_zone_type: str = field(metadata=field_options(alias="heartRateZoneType"))
    min_beats_per_minute: int = field(metadata=field_options(alias="minBeatsPerMinute"))
    max_beats_per_minute: int = field(metadata=field_options(alias="maxBeatsPerMinute"))

    class Config(BaseConfig):
        serialize_by_alias = True


@dataclass
class DailyHeartRateZones(DataClassDictMixin):
    """User's daily heart rate zone thresholds."""

    heart_rate_zones: list[HeartRateZone] = field(
        metadata=field_options(alias="heartRateZones")
    )
    date: Date

    class Config(BaseConfig):
        serialize_by_alias = True


DAILY_VO2_MAX = DataType(
    "daily-vo2-max",
    "dailyVo2Max",
    DailyVO2Max,
    "daily_vo2_max.date",
    read_scopes=[HealthApiScope.MEASUREMENTS_READ],
    write_scopes=[HealthApiScope.MEASUREMENTS_WRITE],
)

DAILY_HEART_RATE_ZONES = DataType(
    "daily-heart-rate-zones",
    "dailyHeartRateZones",
    DailyHeartRateZones,
    "daily_heart_rate_zones.date",
    read_scopes=[HealthApiScope.MEASUREMENTS_READ],
    write_scopes=[HealthApiScope.MEASUREMENTS_WRITE],
)
