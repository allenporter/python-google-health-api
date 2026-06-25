"""Operation models for Google Health API."""

from dataclasses import dataclass, field
from typing import Any

from mashumaro import DataClassDictMixin
from mashumaro.config import BaseConfig


@dataclass
class Status(DataClassDictMixin):
    """The status representation of errors in operations."""

    code: int | None = None
    message: str | None = None
    details: list[dict[str, Any]] = field(default_factory=list)

    class Config(BaseConfig):
        serialize_by_alias = True


@dataclass
class Operation(DataClassDictMixin):
    """Represents a long-running operation."""

    name: str
    metadata: dict[str, Any] = field(default_factory=dict)
    done: bool = False
    error: Status | None = None
    response: dict[str, Any] | None = None

    class Config(BaseConfig):
        serialize_by_alias = True
