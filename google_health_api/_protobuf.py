"""Private, dependency-free protobuf parsing utilities.

This module contains minimal, low-level functions to parse serialized protobuf
binary wire format to extract key fields, avoiding a dependency on the full
`protobuf` package.
"""

from collections.abc import Callable
from typing import Any

# Varint decoding constants
_VARINT_DATA_MASK = 0x7F
_VARINT_CONTINUATION_MASK = 0x80
_VARINT_SHIFT_BITS = 7

# Tag parsing constants
_TAG_FIELD_NUM_SHIFT = 3
_TAG_WIRE_TYPE_MASK = 0x07

# Protobuf wire types
_WIRE_TYPE_VARINT = 0
_WIRE_TYPE_FIXED64 = 1
_WIRE_TYPE_LENGTH_DELIMITED = 2
_WIRE_TYPE_FIXED32 = 5


class ProtobufParseError(ValueError):
    """Raised when there is an issue parsing serialized protobuf bytes."""


def _decode_varint(data: bytes, pos: int) -> tuple[int, int]:
    """Decode a varint from the data starting at pos. Returns (value, next_pos)."""
    val = 0
    shift = 0
    limit = len(data)
    while pos < limit:
        b = data[pos]
        val |= (b & _VARINT_DATA_MASK) << shift
        pos += 1
        if not (b & _VARINT_CONTINUATION_MASK):
            break
        shift += _VARINT_SHIFT_BITS
    return val, pos


def parse_protobuf(
    data: bytes, decoders: dict[int, Callable[[Any], Any]] | None = None
) -> dict[int, Any]:
    """Parse serialized protobuf bytes into a dict of {field_number: value}.

    This scans the serialized protobuf key-value wire format, reading fields
    according to their wire type. Callers can pass a `decoders` dictionary to
    automatically convert parsed values for specific fields (e.g. converting
    raw bytes to integers or strings).
    """
    fields = {}
    pos = 0
    limit = len(data)
    while pos < limit:
        tag, pos = _decode_varint(data, pos)
        field_num = tag >> _TAG_FIELD_NUM_SHIFT
        wire_type = tag & _TAG_WIRE_TYPE_MASK

        if wire_type == _WIRE_TYPE_VARINT:
            val, pos = _decode_varint(data, pos)
        elif wire_type == _WIRE_TYPE_LENGTH_DELIMITED:
            length, pos = _decode_varint(data, pos)
            val = data[pos : pos + length]
            if len(val) < length:
                raise ProtobufParseError(
                    f"Truncated length-delimited field (expected {length} bytes, got {len(val)})"
                )
            pos += length
        elif wire_type == _WIRE_TYPE_FIXED64:
            val = data[pos : pos + 8]
            if len(val) < 8:
                raise ProtobufParseError("Truncated fixed64 field")
            pos += 8
        elif wire_type == _WIRE_TYPE_FIXED32:
            val = data[pos : pos + 4]
            if len(val) < 4:
                raise ProtobufParseError("Truncated fixed32 field")
            pos += 4
        else:
            raise ProtobufParseError(
                f"Unsupported wire type {wire_type} in protobuf structure"
            )

        if decoders and field_num in decoders:
            try:
                val = decoders[field_num](val)
            except Exception as e:
                raise ProtobufParseError(
                    f"Failed to decode field {field_num}: {e}"
                ) from e

        fields[field_num] = val

    return fields
