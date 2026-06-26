"""Health metric data models for Google Health API."""

from dataclasses import dataclass, field

from mashumaro import DataClassDictMixin, field_options
from mashumaro.config import BaseConfig

from .base import DataType


@dataclass
class HeartRate(DataClassDictMixin):
    """Heart rate record."""

    bpm: float
    start_time: str = field(metadata=field_options(alias="startTime"))
    end_time: str = field(metadata=field_options(alias="endTime"))

    class Config(BaseConfig):
        serialize_by_alias = True


HEART_RATE = DataType(
    "heart-rate",
    "heartRate",
    HeartRate,
    "heart_rate.sample_time.physical_time",
)
