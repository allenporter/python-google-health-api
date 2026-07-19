"""Tests for low-level private protobuf parser helper."""

from dataclasses import dataclass, field
from typing import Any
import pytest

from google_health_api._protobuf import (
    FIELD_NUMBER,
    PROTO_TYPE,
    TYPE_BYTES,
    TYPE_INT32,
    TYPE_STRING,
    ProtobufParseError,
    deserialize_protobuf,
)


@dataclass
class SearchRequest:
    """A standard generic protobuf message example class."""

    query: str = field(metadata={FIELD_NUMBER: 1, PROTO_TYPE: TYPE_STRING})
    page_number: int = field(
        metadata={FIELD_NUMBER: 2, PROTO_TYPE: TYPE_INT32}, default=1
    )
    result_per_page: int = field(
        metadata={FIELD_NUMBER: 3, PROTO_TYPE: TYPE_INT32}, default=10
    )


@dataclass
class PhoneNumber:
    """A standard generic phone number protobuf class."""

    number: str = field(metadata={FIELD_NUMBER: 1, PROTO_TYPE: TYPE_STRING})
    type: int = field(metadata={FIELD_NUMBER: 2, PROTO_TYPE: TYPE_INT32}, default=0)


@dataclass
class SearchResult:
    """A standard generic search result protobuf class."""

    url: str = field(metadata={FIELD_NUMBER: 1, PROTO_TYPE: TYPE_STRING})
    title: str = field(metadata={FIELD_NUMBER: 2, PROTO_TYPE: TYPE_STRING})
    snippet_count: int = field(
        metadata={FIELD_NUMBER: 3, PROTO_TYPE: TYPE_INT32}, default=0
    )


@dataclass
class FixedTypesMessage:
    """A helper message to test fixed64/fixed32 wire type deserialization."""

    val64: bytes = field(metadata={FIELD_NUMBER: 1, PROTO_TYPE: TYPE_BYTES})
    val32: bytes = field(metadata={FIELD_NUMBER: 2, PROTO_TYPE: TYPE_BYTES})


@pytest.mark.parametrize(
    "cls,data,expected",
    [
        # Scenario 1: SearchRequest with all fields populated
        (
            SearchRequest,
            b"\x0a\x04test\x10\x02\x18\x14",
            SearchRequest("test", 2, 20),
        ),
        # Scenario 2: SearchRequest with multi-byte varint and default fallbacks
        (
            SearchRequest,
            b"\x0a\x04test\x10\x96\x01",
            SearchRequest("test", 150, 10),
        ),
        # Scenario 3: PhoneNumber with all fields populated
        (
            PhoneNumber,
            b"\x0a\x0b+1-555-0100\x10\x01",
            PhoneNumber("+1-555-0100", 1),
        ),
        # Scenario 4: SearchResult with all fields populated
        (
            SearchResult,
            b"\x0a\x12http://example.com\x12\x0eExample Domain\x18\x05",
            SearchResult("http://example.com", "Example Domain", 5),
        ),
    ],
)
def test_parse_protobuf_decoding(cls: type[Any], data: bytes, expected: Any) -> None:
    """Test that deserialize_protobuf correctly decodes valid protobuf payloads."""
    assert deserialize_protobuf(cls, data) == expected


def test_parse_protobuf_fixed_types() -> None:
    """Test that deserialize_protobuf correctly records fixed64/fixed32 types."""
    # field 1: wire type 1 (fixed64) -> tag (1 << 3) | 1 = 9
    # field 2: wire type 5 (fixed32) -> tag (2 << 3) | 5 = 21
    fixed64_bytes = b"\x01\x02\x03\x04\x05\x06\x07\x08"
    fixed32_bytes = b"\x0a\x0b\x0c\x0d"

    data = b""
    data += bytes([9]) + fixed64_bytes
    data += bytes([21]) + fixed32_bytes

    obj = deserialize_protobuf(FixedTypesMessage, data)
    assert obj.val64 == fixed64_bytes
    assert obj.val32 == fixed32_bytes


@pytest.mark.parametrize(
    "cls,data,error_msg",
    [
        # Scenario 1: Unsupported wire type (group wire type 3)
        (SearchRequest, bytes([11, 1, 2, 3]), "Unsupported wire type"),
        # Scenario 2: Truncated length-delimited field
        (SearchRequest, bytes([10, 4, 1, 2]), "Truncated length-delimited field"),
        # Scenario 3: Truncated fixed64 field
        (FixedTypesMessage, bytes([9, 1, 2, 3]), "Truncated fixed64 field"),
        # Scenario 4: Truncated fixed32 field
        (FixedTypesMessage, bytes([21, 1, 2]), "Truncated fixed32 field"),
    ],
)
def test_parse_protobuf_errors(cls: type[Any], data: bytes, error_msg: str) -> None:
    """Verify that deserialize_protobuf raises ProtobufParseError on malformed inputs."""
    with pytest.raises(ProtobufParseError) as exc_info:
        deserialize_protobuf(cls, data)
    assert error_msg in str(exc_info.value)
