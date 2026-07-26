"""User Settings models for Google Health API."""

from dataclasses import dataclass, field

from mashumaro import DataClassDictMixin, field_options
from mashumaro.config import BaseConfig


@dataclass
class Settings(DataClassDictMixin):
    """User account settings and preferences."""

    name: str
    water_unit: str | None = field(
        metadata=field_options(alias="waterUnit"), default=None
    )
    weight_unit: str | None = field(
        metadata=field_options(alias="weightUnit"), default=None
    )
    food_language_code: str | None = field(
        metadata=field_options(alias="foodLanguageCode"), default=None
    )
    stride_length_walking_type: str | None = field(
        metadata=field_options(alias="strideLengthWalkingType"), default=None
    )
    stride_length_running_type: str | None = field(
        metadata=field_options(alias="strideLengthRunningType"), default=None
    )
    time_zone: str | None = field(
        metadata=field_options(alias="timeZone"), default=None
    )
    auto_stride_enabled: bool | None = field(
        metadata=field_options(alias="autoStrideEnabled"), default=None
    )
    glucose_unit: str | None = field(
        metadata=field_options(alias="glucoseUnit"), default=None
    )
    temperature_unit: str | None = field(
        metadata=field_options(alias="temperatureUnit"), default=None
    )
    language_locale: str | None = field(
        metadata=field_options(alias="languageLocale"), default=None
    )
    utc_offset: str | None = field(
        metadata=field_options(alias="utcOffset"), default=None
    )
    swim_unit: str | None = field(
        metadata=field_options(alias="swimUnit"), default=None
    )
    distance_unit: str | None = field(
        metadata=field_options(alias="distanceUnit"), default=None
    )
    height_unit: str | None = field(
        metadata=field_options(alias="heightUnit"), default=None
    )

    class Config(BaseConfig):
        serialize_by_alias = True
