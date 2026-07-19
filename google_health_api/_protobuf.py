"""Private, dependency-free protobuf parsing utilities.

This module contains minimal, low-level functions to parse serialized protobuf
binary wire format to extract key fields, avoiding a dependency on the full
`protobuf` package.
"""

from collections.abc import Callable
import dataclasses
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

# Dataclass field metadata keys
FIELD_NUMBER = "field_number"
PROTO_TYPE = "proto_type"

# Protobuf logical field types
TYPE_INT32 = "int32"
TYPE_INT64 = "int64"
TYPE_UINT32 = "uint32"
TYPE_UINT64 = "uint64"
TYPE_BYTES = "bytes"
TYPE_STRING = "string"
TYPE_BIG_ENDIAN_INT = "big_endian_int"

# Hardcoded decoders for logical types
_DECODERS: dict[str, Callable[[Any], Any]] = {
    TYPE_INT32: int,
    TYPE_INT64: int,
    TYPE_UINT32: int,
    TYPE_UINT64: int,
    TYPE_BYTES: lambda v: bytes(v) if isinstance(v, (bytes, bytearray)) else v,
    TYPE_STRING: lambda v: v.decode("utf-8") if isinstance(v, bytes) else str(v),
    TYPE_BIG_ENDIAN_INT: lambda v: (
        int.from_bytes(v, byteorder="big") if isinstance(v, bytes) else int(v)
    ),
}


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


def deserialize_protobuf(cls: type[Any], data: bytes) -> Any:
    """Generic helper to parse protobuf bytes and instantiate a tagged dataclass.

    Inspects dataclass fields for 'field_number' and 'proto_type' metadata.
    """
    decoders = {}
    field_map = {}
    default_vals = {}

    for f in dataclasses.fields(cls):
        metadata = f.metadata
        if FIELD_NUMBER in metadata:
            field_num = metadata[FIELD_NUMBER]
            field_map[field_num] = f.name

            # Map the logical proto_type to the hardcoded decoder function
            if PROTO_TYPE in metadata:
                proto_type = metadata[PROTO_TYPE]
                if proto_type in _DECODERS:
                    decoders[field_num] = _DECODERS[proto_type]
                else:
                    raise ProtobufParseError(f"Unsupported proto type: {proto_type}")

            if f.default is not dataclasses.MISSING:
                default_vals[f.name] = f.default
            elif f.default_factory is not dataclasses.MISSING:
                default_vals[f.name] = f.default_factory()

    parsed = parse_protobuf(data, decoders=decoders)

    args = {}
    for field_num, val in parsed.items():
        if field_num in field_map:
            args[field_map[field_num]] = val

    for field_name, default_val in default_vals.items():
        if field_name not in args:
            args[field_name] = default_val

    try:
        return cls(**args)
    except TypeError as e:
        raise ProtobufParseError(
            f"Missing required fields for {cls.__name__}: {e}"
        ) from e
