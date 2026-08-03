"""Nutrition data models for Google Health API."""

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
class WeightQuantity(DataClassDictMixin):
    """Represents a weight quantity."""

    grams: float
    user_provided_unit: str | None = field(
        metadata=field_options(alias="userProvidedUnit"), default=None
    )

    class Config(BaseConfig):
        serialize_by_alias = True


@dataclass
class EnergyQuantity(DataClassDictMixin):
    """Represents an energy quantity."""

    kcal: float
    user_provided_unit: str | None = field(
        metadata=field_options(alias="userProvidedUnit"), default=None
    )

    class Config(BaseConfig):
        serialize_by_alias = True


@dataclass
class Serving(DataClassDictMixin):
    """Represents a serving of food."""

    food_measurement_unit: str | None = field(
        metadata=field_options(alias="foodMeasurementUnit"), default=None
    )
    amount: float | None = None
    food_measurement_unit_display_name: str | None = field(
        metadata=field_options(alias="foodMeasurementUnitDisplayName"), default=None
    )

    class Config(BaseConfig):
        serialize_by_alias = True


@dataclass
class NutrientQuantity(DataClassDictMixin):
    """Represents a nutrient quantity."""

    quantity: WeightQuantity
    nutrient: str

    class Config(BaseConfig):
        serialize_by_alias = True


@dataclass
class NutritionLog(DataClassDictMixin):
    """Holds information about a user logged food."""

    interval: SessionTimeInterval
    food: str | None = None
    food_display_name: str | None = field(
        metadata=field_options(alias="foodDisplayName"), default=None
    )
    meal_type: str | None = field(
        metadata=field_options(alias="mealType"), default=None
    )
    serving: Serving | None = None
    energy: EnergyQuantity | None = None
    energy_from_fat: EnergyQuantity | None = field(
        metadata=field_options(alias="energyFromFat"), default=None
    )
    total_fat: WeightQuantity | None = field(
        metadata=field_options(alias="totalFat"), default=None
    )
    total_carbohydrate: WeightQuantity | None = field(
        metadata=field_options(alias="totalCarbohydrate"), default=None
    )
    nutrients: list[NutrientQuantity] = field(default_factory=list)

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
class WeightQuantityRollup(DataClassDictMixin):
    """Rollup for weight quantity."""

    grams_sum: float = field(metadata=field_options(alias="gramsSum"))
    user_provided_unit_last: str | None = field(
        metadata=field_options(alias="userProvidedUnitLast"), default=None
    )

    class Config(BaseConfig):
        serialize_by_alias = True


@dataclass
class EnergyQuantityRollup(DataClassDictMixin):
    """Rollup for energy quantity."""

    kcal_sum: float = field(metadata=field_options(alias="kcalSum"))
    user_provided_unit_last: str | None = field(
        metadata=field_options(alias="userProvidedUnitLast"), default=None
    )

    class Config(BaseConfig):
        serialize_by_alias = True


@dataclass
class NutrientQuantityRollup(DataClassDictMixin):
    """Rollup for nutrient quantity."""

    quantity: WeightQuantityRollup
    nutrient: str

    class Config(BaseConfig):
        serialize_by_alias = True


@dataclass
class NutritionLogRollupValue(DataClassDictMixin):
    """Represents the rollup of nutrition log."""

    energy: EnergyQuantityRollup | None = None
    energy_from_fat: EnergyQuantityRollup | None = field(
        metadata=field_options(alias="energyFromFat"), default=None
    )
    total_fat: WeightQuantityRollup | None = field(
        metadata=field_options(alias="totalFat"), default=None
    )
    total_carbohydrate: WeightQuantityRollup | None = field(
        metadata=field_options(alias="totalCarbohydrate"), default=None
    )
    nutrients: list[NutrientQuantityRollup] = field(default_factory=list)

    class Config(BaseConfig):
        serialize_by_alias = True


NUTRITION_LOG = DataType(
    "nutrition-log",
    "nutritionLog",
    NutritionLog,
    "nutrition_log.interval.civil_start_time",
    NutritionLogRollupValue,
    read_scopes=[HealthApiScope.NUTRITION_READ],
    write_scopes=[HealthApiScope.NUTRITION_WRITE],
)
