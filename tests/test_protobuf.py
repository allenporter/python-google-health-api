"""Tests for low-level private protobuf parser helper."""

import base64
import pytest

from google_health_api._protobuf import ProtobufParseError, parse_protobuf


def test_parse_protobuf_keyset_snapshot() -> None:
    """Test that parse_protobuf correctly decodes a real-world Google Tink ECDSA key value."""
    # Real base64 value from:
    # https://www.gstatic.com/googlehealthapi/webhooks/webhooks_public_keyset.json
    base64_val = (
        "EgYIAxACGAIaIQBDWg3kaiabjtrVXbSSbcn6e3QqiCLD+B4GuhC/Z1C6miIhACarm0VQv9W"
        "jNZG/AB0itXCIGFW5ddInmBFUjK/8w0v3"
    )
    raw_bytes = base64.b64decode(base64_val)

    fields = parse_protobuf(raw_bytes)

    # Expected key structures inside Tink EcdsaPublicKey:
    # Field 2 (params): Represents serialized params EcdsaParams
    # Field 3 (x): X Coordinate bytes
    # Field 4 (y): Y Coordinate bytes
    assert fields[2] == b"\x08\x03\x10\x02\x18\x02"
    assert (
        fields[3]
        == b'\x00CZ\r\xe4j&\x9b\x8e\xda\xd5]\xb4\x92m\xc9\xfa\x7bt*\x88"\xc3\xf8'
        b"\x1e\x06\xba\x10\xbfgP\xba\x9a"
    )
    assert (
        fields[4]
        == b"\x00&\xab\x9bE\x50\xbf\xd5\xa3\x35\x91\xbf\x00\x1d\x22\xb5\x70\x88\x18"
        b"\x55\xb9\x75\xd2\x27\x98\x11\x54\x8c\xaf\xfc\xc3\x4b\xf7"
    )


def test_parse_protobuf_unsupported_wire_type() -> None:
    """Verify that parse_protobuf raises ProtobufParseError on unsupported wire types."""
    # Create a tag with field_number 1 and wire type 3 (Groups - deprecated/unsupported wire type)
    # tag = (1 << 3) | 3 = 11
    data = bytes([11, 1, 2, 3])
    with pytest.raises(ProtobufParseError) as exc_info:
        parse_protobuf(data)
    assert "Unsupported wire type" in str(exc_info.value)


def test_parse_protobuf_truncated() -> None:
    """Verify that parse_protobuf raises ProtobufParseError on truncated inputs."""
    # tag 26 represents field 3 wire type 2 (length delimited).
    # Length specifies 32 bytes, but we provide only 5 bytes.
    truncated_data = bytes([26, 32, 1, 2, 3, 4, 5])
    with pytest.raises(ProtobufParseError) as exc_info:
        parse_protobuf(truncated_data)
    assert "Truncated length-delimited field" in str(exc_info.value)
