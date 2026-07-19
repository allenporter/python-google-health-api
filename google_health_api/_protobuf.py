"""Private, dependency-free protobuf parsing utilities.

This module contains minimal, low-level functions to parse serialized protobuf
binary wire format and map them directly into Python dataclasses using field
metadata. This avoids a dependency on the full compiled `protobuf` package.

Example:
    Given the Protobuf definition:
    ```proto
    message MyProtoMessage {
      uint32 version = 1;
      bytes payload = 2;
    }
    ```

    The corresponding Python dataclass:
    ```python
    from dataclasses import dataclass, field
    from google_health_api._protobuf import (
        FIELD_NUMBER,
        PROTO_TYPE,
        TYPE_BYTES,
        TYPE_UINT32,
        deserialize_protobuf,
    )

    @dataclass
    class MyProtoMessage:
        version: int = field(
            metadata={FIELD_NUMBER: 1, PROTO_TYPE: TYPE_UINT32}, default=0
        )
        payload: bytes = field(metadata={FIELD_NUMBER: 2, PROTO_TYPE: TYPE_BYTES})

    # Decode the message
    message = deserialize_protobuf(MyProtoMessage, serialized_bytes)
    ```
"""

from collections.abc import Callable
import dataclasses
from functools import cache
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

# Dataclass field metadata keys used to map fields to protobuf definitions
FIELD_NUMBER = "field_number"  # The integer field number in the protobuf definition
PROTO_TYPE = "proto_type"  # The logical protobuf type name (e.g. TYPE_BIG_ENDIAN_INT)

# Protobuf logical field types supported by the parser
TYPE_INT32 = "int32"
TYPE_INT64 = "int64"
TYPE_UINT32 = "uint32"
TYPE_UINT64 = "uint64"
TYPE_BYTES = "bytes"
TYPE_STRING = "string"
TYPE_BIG_ENDIAN_INT = (
    "big_endian_int"  # Decodes length-delimited bytes as a big-endian integer
)

# Hardcoded decoders for logical types
_DECODERS: dict[str, Callable[[Any], Any]] = {
    TYPE_INT32: int,
    TYPE_INT64: int,
    TYPE_UINT32: int,
    TYPE_UINT64: int,
    TYPE_BYTES: lambda v: v,
    TYPE_STRING: lambda v: v.decode("utf-8"),
    TYPE_BIG_ENDIAN_INT: lambda v: int.from_bytes(v, byteorder="big"),
}


class ProtobufParseError(ValueError):
    """Raised when there is an issue parsing serialized protobuf bytes."""


@dataclasses.dataclass
class _ProtoFieldMetadata:
    """Contains parsing metadata for a single protobuf dataclass field."""

    field_name: str
    decoder: Callable[[Any], Any] | None = None


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


@cache
def _extract_proto_metadata(cls: type[Any]) -> dict[int, _ProtoFieldMetadata]:
    """Extracts field mapping, decoders, and default values from dataclass metadata."""
    field_metadata = {}

    for f in dataclasses.fields(cls):
        metadata = f.metadata
        if FIELD_NUMBER not in metadata:
            continue

        field_num = metadata[FIELD_NUMBER]
        decoder = None

        # Map the logical proto_type to the hardcoded decoder function
        if PROTO_TYPE in metadata:
            proto_type = metadata[PROTO_TYPE]
            if proto_type in _DECODERS:
                decoder = _DECODERS[proto_type]
            else:
                raise ProtobufParseError(f"Unsupported proto type: {proto_type}")

        field_metadata[field_num] = _ProtoFieldMetadata(
            field_name=f.name,
            decoder=decoder,
        )

    return field_metadata


def deserialize_protobuf(cls: type[Any], data: bytes) -> Any:
    """Generic helper to parse protobuf bytes and instantiate a tagged dataclass.

    This function inspects the dataclass fields for `FIELD_NUMBER` and `PROTO_TYPE`
    keys in their field metadata dictionary. It then parses the binary protobuf
    wire format and applies the appropriate logical decoders (e.g. decoding
    bytes to strings or coordinates to integers) before instantiating the class.

    Args:
        cls: The target dataclass type to instantiate.
        data: The serialized protobuf bytes.

    Returns:
        An instance of the target dataclass `cls` populated with parsed values.

    Raises:
        ProtobufParseError: If parsing fails due to malformed wire tags, unsupported
            types, or missing required fields.
    """
    field_metadata = _extract_proto_metadata(cls)

    args = {}
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

        if field_num in field_metadata:
            f_meta = field_metadata[field_num]
            if f_meta.decoder:
                try:
                    val = f_meta.decoder(val)
                except Exception as e:
                    raise ProtobufParseError(
                        f"Failed to decode field {field_num}: {e}"
                    ) from e
            args[f_meta.field_name] = val

    try:
        return cls(**args)
    except TypeError as e:
        raise ProtobufParseError(
            f"Missing required fields for {cls.__name__}: {e}"
        ) from e
