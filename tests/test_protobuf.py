"""Tests for low-level private protobuf parser helper."""

import base64
from dataclasses import dataclass, field
import pytest

from google_health_api._protobuf import (
    FIELD_NUMBER,
    PROTO_TYPE,
    TYPE_BIG_ENDIAN_INT,
    TYPE_BYTES,
    TYPE_UINT32,
    ProtobufParseError,
    deserialize_protobuf,
)


@dataclass
class TinkEcdsaPublicKey:
    params: bytes = field(metadata={FIELD_NUMBER: 2, PROTO_TYPE: TYPE_BYTES})
    x: int = field(metadata={FIELD_NUMBER: 3, PROTO_TYPE: TYPE_BIG_ENDIAN_INT})
    y: int = field(metadata={FIELD_NUMBER: 4, PROTO_TYPE: TYPE_BIG_ENDIAN_INT})
    version: int = field(metadata={FIELD_NUMBER: 1, PROTO_TYPE: TYPE_UINT32}, default=0)


@dataclass
class DummyBytesField:
    value: bytes = field(metadata={FIELD_NUMBER: 1, PROTO_TYPE: TYPE_BYTES})


@dataclass
class DummyFixedField:
    # We map field 1 (fixed64) and field 2 (fixed32)
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

    key = deserialize_protobuf(TinkEcdsaPublicKey, raw_bytes)

    # Expected key structures inside Tink EcdsaPublicKey:
    assert key.version == 0
    assert key.params == b"\x08\x03\x10\x02\x18\x02"
    assert (
        key.x
        == 30464072971658236180623026012261445907865018865466996670004259804604043147930
    )
    assert (
        key.y
        == 17491090733665198527707448657584605832598762999353660226629372998000048294903
    )


def test_parse_protobuf_unsupported_wire_type() -> None:
    """Verify that deserialize_protobuf raises ProtobufParseError on unsupported wire types."""
    # Create a tag with field_number 1 and wire type 3 (Groups - deprecated/unsupported wire type)
    # tag = (1 << 3) | 3 = 11
    data = bytes([11, 1, 2, 3])
    with pytest.raises(ProtobufParseError) as exc_info:
        deserialize_protobuf(DummyBytesField, data)
    assert "Unsupported wire type" in str(exc_info.value)


def test_parse_protobuf_truncated() -> None:
    """Verify that deserialize_protobuf raises ProtobufParseError on truncated inputs."""
    # tag 26 represents field 3 wire type 2 (length delimited).
    # Length specifies 32 bytes, but we provide only 5 bytes.
    truncated_data = bytes([26, 32, 1, 2, 3, 4, 5])
    with pytest.raises(ProtobufParseError) as exc_info:
        deserialize_protobuf(DummyBytesField, truncated_data)
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

    obj = deserialize_protobuf(DummyFixedField, data)
    assert obj.val64 == fixed64_bytes
    assert obj.val32 == fixed32_bytes


def test_parse_protobuf_fixed64_truncated() -> None:
    """Verify that deserialize_protobuf raises ProtobufParseError on truncated fixed64 fields."""
    # field 1: wire type 1 (fixed64) -> tag (1 << 3) | 1 = 9
    truncated_fixed64 = bytes([9, 1, 2, 3])
    with pytest.raises(ProtobufParseError) as exc_info:
        deserialize_protobuf(DummyFixedField, truncated_fixed64)
    assert "Truncated fixed64 field" in str(exc_info.value)


def test_parse_protobuf_fixed32_truncated() -> None:
    """Verify that deserialize_protobuf raises ProtobufParseError on truncated fixed32 fields."""
    # field 2: wire type 5 (fixed32) -> tag (2 << 3) | 5 = 21
    truncated_fixed32 = bytes([21, 1, 2])
    with pytest.raises(ProtobufParseError) as exc_info:
        deserialize_protobuf(DummyFixedField, truncated_fixed32)
    assert "Truncated fixed32 field" in str(exc_info.value)
