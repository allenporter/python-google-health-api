"""Heart health data models for Google Health API."""

from dataclasses import dataclass, field

from mashumaro import DataClassDictMixin, field_options
from mashumaro.config import BaseConfig

from ..const import HealthApiScope
from .base import DataType
from .sleep import CivilDateTime, SessionTimeInterval


class BaseConfig(BaseConfig):
    """Base mashumaro configuration."""

    serialize_by_alias = True


@dataclass
class MedicalDeviceInfo(DataClassDictMixin):
    """Software as Medical Device (SaMD) metadata."""

    firmware_version: str | None = field(
        metadata=field_options(alias="firmwareVersion"), default=None
    )
    service_version: str | None = field(
        metadata=field_options(alias="serviceVersion"), default=None
    )
    algorithm_version: str | None = field(
        metadata=field_options(alias="algorithmVersion"), default=None
    )
    feature_version: str | None = field(
        metadata=field_options(alias="featureVersion"), default=None
    )
    device_model: str | None = field(
        metadata=field_options(alias="deviceModel"), default=None
    )

    class Config(BaseConfig):
        serialize_by_alias = True


@dataclass
class HeartBeat(DataClassDictMixin):
    """A single heart beat measurement."""

    physical_time: str = field(metadata=field_options(alias="physicalTime"))
    utc_offset: str = field(metadata=field_options(alias="utcOffset"))
    beats_per_minute: int = field(metadata=field_options(alias="beatsPerMinute"))
    civil_time: CivilDateTime | None = field(
        metadata=field_options(alias="civilTime"), default=None
    )

    class Config(BaseConfig):
        serialize_by_alias = True


@dataclass
class AlertWindow(DataClassDictMixin):
    """An analysis window evaluated for AFib."""

    start_time: str = field(metadata=field_options(alias="startTime"))
    start_utc_offset: str = field(metadata=field_options(alias="startUtcOffset"))
    end_time: str = field(metadata=field_options(alias="endTime"))
    end_utc_offset: str = field(metadata=field_options(alias="endUtcOffset"))
    positive: bool | None = field(default=None)
    heart_beats: list[HeartBeat] = field(
        metadata=field_options(alias="heartBeats"), default_factory=list
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
class IrregularRhythmNotification(DataClassDictMixin):
    """Represents an Irregular Rhythm Notification alert."""

    interval: SessionTimeInterval
    alert_windows: list[AlertWindow] = field(
        metadata=field_options(alias="alertWindows"), default_factory=list
    )
    medical_device_info: MedicalDeviceInfo | None = field(
        metadata=field_options(alias="medicalDeviceInfo"), default=None
    )

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


@dataclass
class Electrocardiogram(DataClassDictMixin):
    """Represents an Electrocardiogram (ECG) measurement session."""

    interval: SessionTimeInterval
    result_classification: str | None = field(
        metadata=field_options(alias="resultClassification"), default=None
    )
    sampling_frequency_hertz: int | None = field(
        metadata=field_options(alias="samplingFrequencyHertz"), default=None
    )
    millivolts_scaling_factor: int | None = field(
        metadata=field_options(alias="millivoltsScalingFactor"), default=None
    )
    beats_per_minute_avg: int | None = field(
        metadata=field_options(alias="beatsPerMinuteAvg"), default=None
    )
    medical_device_info: MedicalDeviceInfo | None = field(
        metadata=field_options(alias="medicalDeviceInfo"), default=None
    )
    waveform_samples: list[int] = field(
        metadata=field_options(alias="waveformSamples"), default_factory=list
    )
    lead_number: int | None = field(
        metadata=field_options(alias="leadNumber"), default=None
    )

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


ELECTROCARDIOGRAM = DataType(
    "electrocardiogram",
    "electrocardiogram",
    Electrocardiogram,
    "electrocardiogram.interval.start_time",
    read_scopes=[HealthApiScope.MEASUREMENTS_READ],
    write_scopes=[HealthApiScope.MEASUREMENTS_WRITE],
)

IRREGULAR_RHYTHM_NOTIFICATION = DataType(
    "irregular-rhythm-notification",
    "irregularRhythmNotification",
    IrregularRhythmNotification,
    "irregular_rhythm_notification.interval.civil_start_time",
    read_scopes=[HealthApiScope.MEASUREMENTS_READ],
    write_scopes=[HealthApiScope.MEASUREMENTS_WRITE],
)
