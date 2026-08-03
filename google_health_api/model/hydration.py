"""Hydration data models for Google Health API."""

from dataclasses import dataclass, field

from mashumaro import DataClassDictMixin, field_options
from mashumaro.config import BaseConfig

from ..const import HealthApiScope
from .base import DataType
from .sleep import SessionTimeInterval


class BaseConfig(BaseConfig):
    """Base mashumaro configuration."""

    serialize_by_alias = True


@dataclass
class VolumeQuantity(DataClassDictMixin):
    """Represents a volume quantity."""

    milliliters: float
    user_provided_unit: str | None = field(
        metadata=field_options(alias="userProvidedUnit"), default=None
    )

    class Config(BaseConfig):
        serialize_by_alias = True


@dataclass
class HydrationLog(DataClassDictMixin):
    """Holds information about a user logged hydration."""

    amount_consumed: VolumeQuantity = field(
        metadata=field_options(alias="amountConsumed")
    )
    interval: SessionTimeInterval

    @property
    def start_time(self) -> str:
        """Return the start time of the interval."""
        return self.interval.start_time

    @property
    def end_time(self) -> str | None:
        """Return the end time of the interval."""
        return self.interval.end_time if self.interval else None

    class Config(BaseConfig):
        serialize_by_alias = True


@dataclass
class VolumeQuantityRollup(DataClassDictMixin):
    """Rollup for volume quantity."""

    milliliters_sum: float = field(metadata=field_options(alias="millilitersSum"))
    user_provided_unit_last: str | None = field(
        metadata=field_options(alias="userProvidedUnitLast"), default=None
    )

    class Config(BaseConfig):
        serialize_by_alias = True


@dataclass
class HydrationLogRollupValue(DataClassDictMixin):
    """Represents the rollup of hydration log."""

    amount_consumed: VolumeQuantityRollup = field(
        metadata=field_options(alias="amountConsumed")
    )

    class Config(BaseConfig):
        serialize_by_alias = True


HYDRATION_LOG = DataType(
    "hydration-log",
    "hydrationLog",
    HydrationLog,
    "hydration_log.interval.civil_start_time",
    HydrationLogRollupValue,
    read_scopes=[HealthApiScope.NUTRITION_READ],
    write_scopes=[HealthApiScope.NUTRITION_WRITE],
)
