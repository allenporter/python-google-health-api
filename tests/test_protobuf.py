"""Tests for low-level private protobuf parser helper."""

import base64
from dataclasses import dataclass, field
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
from google_health_api.keyset import EcdsaPublicKey


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
class FixedTypesMessage:
    """A helper message to test fixed64/fixed32 wire type deserialization."""

    val64: bytes = field(metadata={FIELD_NUMBER: 1, PROTO_TYPE: TYPE_BYTES})
    val32: bytes = field(metadata={FIELD_NUMBER: 2, PROTO_TYPE: TYPE_BYTES})


def test_parse_protobuf_keyset_snapshot() -> None:
    """Test that deserialize_protobuf correctly decodes a real-world Google Tink ECDSA key value."""
    # Real base64 value from:
    # https://www.gstatic.com/googlehealthapi/webhooks/webhooks_public_keyset.json
    base64_val = (
        "EgYIAxACGAIaIQBDWg3kaiabjtrVXbSSbcn6e3QqiCLD+B4GuhC/Z1C6miIhACarm0VQv9W"
        "jNZG/AB0itXCIGFW5ddInmBFUjK/8w0v3"
    )
    raw_bytes = base64.b64decode(base64_val)

    key = deserialize_protobuf(EcdsaPublicKey, raw_bytes)

    # Expected key structures inside Tink EcdsaPublicKey:
    assert key.version == 0
    assert (
        key.x
        == 30464072971658236180623026012261445907865018865466996670004259804604043147930
    )
    assert (
        key.y
        == 17491090733665198527707448657584605832598762999353660226629372998000048294903
    )


def test_parse_protobuf_generic_decoding() -> None:
    """Test standard decoding of query, varint parameters, and default values."""
    # field 1 (query, length delimited): tag 10, length 4, value b"test" -> b"\x0a\x04test"
    # field 2 (page_number, varint): tag 16, value 2 -> b"\x10\x02"
    # field 3 (result_per_page, varint): tag 24, value 20 -> b"\x18\x14"
    data = b"\x0a\x04test\x10\x02\x18\x14"

    req = deserialize_protobuf(SearchRequest, data)
    assert req.query == "test"
    assert req.page_number == 2
    assert req.result_per_page == 20


def test_parse_protobuf_default_fallbacks() -> None:
    """Verify that omitted message fields fallback to their standard dataclass defaults."""
    # Only serialize the name/query field
    data = b"\x0a\x04test"

    req = deserialize_protobuf(SearchRequest, data)
    assert req.query == "test"
    assert req.page_number == 1
    assert req.result_per_page == 10


def test_parse_protobuf_unsupported_wire_type() -> None:
    """Verify that deserialize_protobuf raises ProtobufParseError on unsupported wire types."""
    # Create a tag with field_number 1 and wire type 3 (Groups - deprecated/unsupported wire type)
    # tag = (1 << 3) | 3 = 11
    data = bytes([11, 1, 2, 3])
    with pytest.raises(ProtobufParseError) as exc_info:
        deserialize_protobuf(SearchRequest, data)
    assert "Unsupported wire type" in str(exc_info.value)


def test_parse_protobuf_truncated() -> None:
    """Verify that deserialize_protobuf raises ProtobufParseError on truncated inputs."""
    # tag 10 represents field 1 wire type 2 (length delimited).
    # Length specifies 4 bytes, but we provide only 2 bytes.
    truncated_data = bytes([10, 4, 1, 2])
    with pytest.raises(ProtobufParseError) as exc_info:
        deserialize_protobuf(SearchRequest, truncated_data)
    assert "Truncated length-delimited field" in str(exc_info.value)


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


def test_parse_protobuf_fixed64_truncated() -> None:
    """Verify that deserialize_protobuf raises ProtobufParseError on truncated fixed64 fields."""
    # field 1: wire type 1 (fixed64) -> tag (1 << 3) | 1 = 9
    truncated_fixed64 = bytes([9, 1, 2, 3])
    with pytest.raises(ProtobufParseError) as exc_info:
        deserialize_protobuf(FixedTypesMessage, truncated_fixed64)
    assert "Truncated fixed64 field" in str(exc_info.value)


def test_parse_protobuf_fixed32_truncated() -> None:
    """Verify that deserialize_protobuf raises ProtobufParseError on truncated fixed32 fields."""
    # field 2: wire type 5 (fixed32) -> tag (2 << 3) | 5 = 21
    truncated_fixed32 = bytes([21, 1, 2])
    with pytest.raises(ProtobufParseError) as exc_info:
        deserialize_protobuf(FixedTypesMessage, truncated_fixed32)
    assert "Truncated fixed32 field" in str(exc_info.value)
