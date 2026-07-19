"""Private, dependency-free protobuf parsing utilities.

This module contains minimal, low-level functions to parse serialized protobuf
binary wire format to extract key fields, avoiding a dependency on the full
`protobuf` package.
"""

from typing import Any


class ProtobufParseError(ValueError):
    """Raised when there is an issue parsing serialized protobuf bytes."""


def _decode_varint(data: bytes, pos: int) -> tuple[int, int]:
    """Decode a varint from the data starting at pos. Returns (value, next_pos)."""
    val = 0
    shift = 0
    limit = len(data)
    while pos < limit:
        b = data[pos]
        val |= (b & 0x7F) << shift
        pos += 1
        if not (b & 0x80):
            break
        shift += 7
    return val, pos


def parse_protobuf(data: bytes) -> dict[int, Any]:
    """Parse serialized protobuf bytes into a dict of {field_number: value}.

    This scans the serialized protobuf key-value wire format, reading fields
    according to their wire type.
    """
    fields = {}
    pos = 0
    limit = len(data)
    while pos < limit:
        tag, pos = _decode_varint(data, pos)
        field_num = tag >> 3
        wire_type = tag & 0x07
        if wire_type == 0:
            val, pos = _decode_varint(data, pos)
            fields[field_num] = val
        elif wire_type == 2:
            length, pos = _decode_varint(data, pos)
            val = data[pos : pos + length]
            pos += length
            fields[field_num] = val
        elif wire_type == 1:
            pos += 8
        elif wire_type == 5:
            pos += 4
        else:
            raise ProtobufParseError(
                f"Unsupported wire type {wire_type} in protobuf structure"
            )
    return fields
