"""User Profile and Identity models for Google Health API."""

from dataclasses import dataclass, field
from mashumaro import DataClassDictMixin, field_options
from mashumaro.config import BaseConfig


@dataclass
class Date(DataClassDictMixin):
    """Represents a whole or partial calendar date."""

    year: int | None = None
    month: int | None = None
    day: int | None = None

    class Config(BaseConfig):
        serialize_by_alias = True


@dataclass
class Profile(DataClassDictMixin):
    """User profile details."""

    name: str
    age: int | None = None
    membership_start_date: Date | None = field(
        metadata=field_options(alias="membershipStartDate"), default=None
    )
    user_configured_running_stride_length_mm: int | None = field(
        metadata=field_options(alias="userConfiguredRunningStrideLengthMm"),
        default=None,
    )
    auto_running_stride_length_mm: int | None = field(
        metadata=field_options(alias="autoRunningStrideLengthMm"), default=None
    )
    user_configured_walking_stride_length_mm: int | None = field(
        metadata=field_options(alias="userConfiguredWalkingStrideLengthMm"),
        default=None,
    )
    auto_walking_stride_length_mm: int | None = field(
        metadata=field_options(alias="autoWalkingStrideLengthMm"), default=None
    )

    class Config(BaseConfig):
        serialize_by_alias = True


@dataclass
class IrnProfile(DataClassDictMixin):
    """Irregular Rhythm Notifications (IRN) Profile details."""

    name: str
    onboarding_status: bool = field(
        metadata=field_options(alias="onboardingStatus"), default=False
    )
    enrollment_status: bool = field(
        metadata=field_options(alias="enrollmentStatus"), default=False
    )
    update_time: str | None = field(
        metadata=field_options(alias="updateTime"), default=None
    )

    class Config(BaseConfig):
        serialize_by_alias = True


@dataclass
class Identity(DataClassDictMixin):
    """Details about the Google user's identity (mapping Google and legacy Fitbit IDs)."""

    name: str
    health_user_id: str | None = field(
        metadata=field_options(alias="healthUserId"), default=None
    )
    legacy_user_id: str | None = field(
        metadata=field_options(alias="legacyUserId"), default=None
    )

    class Config(BaseConfig):
        serialize_by_alias = True
