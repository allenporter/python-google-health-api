"""User Profile and Identity models for Google Health API."""

import datetime as dt
from dataclasses import dataclass, field
from typing import Self

from mashumaro import DataClassDictMixin, field_options
from mashumaro.config import BaseConfig

from .base import ModelConfig


@dataclass
class Date(DataClassDictMixin):
    """Represents a whole or partial calendar date."""

    year: int | None = None
    month: int | None = None
    day: int | None = None

    @classmethod
    def from_date(cls, value: dt.date) -> Self:
        """Create a Date from a standard library date object."""
        return cls(year=value.year, month=value.month, day=value.day)

    def to_date(self) -> dt.date | None:
        """Convert to a standard library date if year, month, and day are set."""
        if not self.year or not self.month or not self.day:
            return None
        return dt.date(self.year, self.month, self.day)

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
    update_time: dt.datetime | None = field(
        metadata=field_options(alias="updateTime"), default=None
    )

    class Config(ModelConfig):
        pass


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


@dataclass
class UserInfo(DataClassDictMixin):
    """User info details from Google OAuth2 userinfo endpoint."""

    sub: str
    name: str | None = None
    given_name: str | None = field(
        metadata=field_options(alias="given_name"), default=None
    )
    family_name: str | None = field(
        metadata=field_options(alias="family_name"), default=None
    )
    picture: str | None = None
    email: str | None = None
    email_verified: bool | None = field(
        metadata=field_options(alias="email_verified"), default=None
    )
    locale: str | None = None

    @property
    def display_name(self) -> str | None:
        """Alias for name, which acts as the user's display name."""
        return self.name

    class Config(BaseConfig):
        serialize_by_alias = True
