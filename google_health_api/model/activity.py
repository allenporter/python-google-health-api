"""Activity data models for Google Health API."""

from dataclasses import dataclass, field

from mashumaro import DataClassDictMixin, field_options
from mashumaro.config import BaseConfig

from .base import DataType


@dataclass
class Steps(DataClassDictMixin):
    """Step count record."""

    count: int
    start_time: str = field(metadata=field_options(alias="startTime"))
    end_time: str = field(metadata=field_options(alias="endTime"))

    class Config(BaseConfig):
        serialize_by_alias = True


STEPS = DataType("steps", "steps", Steps, "steps.interval.start_time")
