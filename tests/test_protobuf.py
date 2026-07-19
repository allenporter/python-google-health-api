"""Tests for low-level private protobuf parser helper."""

import base64
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


@pytest.mark.parametrize(
    "data,expected",
    [
        # Scenario 1: Decode all fields
        (b"\x0a\x04test\x10\x02\x18\x14", SearchRequest("test", 2, 20)),
        # Scenario 2: Omitted fields fall back to dataclass defaults
        (b"\x0a\x04test", SearchRequest("test", 1, 10)),
    ],
)
def test_parse_protobuf_decoding(data: bytes, expected: SearchRequest) -> None:
    """Test that deserialize_protobuf correctly decodes valid protobuf payloads."""
    assert deserialize_protobuf(SearchRequest, data) == expected


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
