"""Google Health API Webhook Keyset Parsing and Signature Verification.

This module provides structures and functions to parse Google Tink public keysets
and verify ECDSA signatures on webhook notifications.

## Rationale for Not Using the Tink Library Direct Dependency

Google Health API webhooks sign JSON payloads with a private key, and the public
keyset is hosted as a Google Tink JSON keyset. The official Tink library (`tink`)
is a Python wrapper around a native C++ engine.

We avoid using the official `tink` library directly for the following reasons:
1. **Compilation issues:** On non-standard platforms, newer Python versions, or
   lightweight environments like Alpine Linux (common in Docker) and serverless
   runtimes (AWS Lambda, Google Cloud Functions), precompiled wheels for `tink`
   are often unavailable. Compiling it from source requires Bazel and protobuf
   compilers, which creates significant deployment friction.
2. **Library Size:** Tink adds substantial binary bloat to what should be a
   lightweight client SDK.

Instead, we use Python's standard `cryptography` library (which wraps OpenSSL/Rust
and has precompiled wheels everywhere). This module manually performs the parsing
of the Tink JSON container and protobuf-encoded key material, and delegating the
actual signature verification to `cryptography`. This does not violate the "never
write your own cryptography" rule as the cryptographic operations are fully
handled by a highly vetted, industry-standard library.

For more details on signature verification, see the official documentation:
https://developers.google.com/health/webhooks#how_to_verify_the_signature

## Threat Model & Security Assumptions

1. **Keyset Source Trust:** It is assumed that the JSON keyset data is retrieved
   from Google's official public endpoint over a secure TLS connection
   (https://www.gstatic.com/googlehealthapi/webhooks/webhooks_public_keyset.json)
   and has not been altered prior to parsing.
2. **Timing Attacks Protection:** Signature verification is fully delegated to
   Python's `cryptography` library, utilizing OpenSSL's constant-time validation
   routines to resist side-channel timing attacks.
3. **Denial of Service (DoS) Prevention:** The low-level protobuf deserializer
   strictly limits binary payload parsing size to 64 KB to mitigate resource
   exhaustion attempts with large malicious payloads.
4. **Key Configuration Safety:** Only keys explicitly marked as `"ENABLED"`
   are allowed to verify signatures. Disabled keys are ignored.
"""

import base64
from dataclasses import dataclass, field
from functools import cached_property

from mashumaro import DataClassDictMixin, field_options
from mashumaro.config import BaseConfig

from ._protobuf import (
    FIELD_NUMBER,
    PROTO_TYPE,
    TYPE_BIG_ENDIAN_INT,
    TYPE_UINT32,
    ProtobufParseError,
    deserialize_protobuf,
)

try:
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import ec

    _HAS_CRYPTOGRAPHY = True
except ImportError:

    class InvalidSignature(Exception):
        pass

    _HAS_CRYPTOGRAPHY = False


class KeysetError(ValueError):
    """Raised when there is an issue parsing the Tink keyset or key material."""


class SignatureVerificationError(ValueError):
    """Raised when the webhook signature verification fails."""


@dataclass
class EcdsaPublicKey:
    """Represents a Tink-encoded ECDSA P-256 public key.

    Parsed from the serialized protobuf representation:
    https://github.com/tink-crypto/tink-java/blob/main/proto/ecdsa.proto
    """

    x: int = field(metadata={FIELD_NUMBER: 3, PROTO_TYPE: TYPE_BIG_ENDIAN_INT})
    y: int = field(metadata={FIELD_NUMBER: 4, PROTO_TYPE: TYPE_BIG_ENDIAN_INT})
    version: int = field(metadata={FIELD_NUMBER: 1, PROTO_TYPE: TYPE_UINT32}, default=0)

    @classmethod
    def deserialize(cls, data: bytes) -> ec.EllipticCurvePublicKey:
        """Deserialize key material and construct a cryptography public key.

        Raises:
            KeysetError: If parsing or construction fails.
        """
        try:
            proto = deserialize_protobuf(cls, data)
        except ProtobufParseError as e:
            raise KeysetError("Failed to parse key protobuf data") from e
        return proto.to_cryptography_key()

    def to_cryptography_key(self) -> ec.EllipticCurvePublicKey:
        """Converts this key to a cryptography EllipticCurvePublicKey.

        Raises:
            KeysetError: If constructing the curve public key fails.
        """
        if not _HAS_CRYPTOGRAPHY:
            raise KeysetError("The cryptography library is not installed.")
        try:
            public_numbers = ec.EllipticCurvePublicNumbers(
                x=self.x,
                y=self.y,
                curve=ec.SECP256R1(),
            )
            return public_numbers.public_key()
        except ValueError as e:
            raise KeysetError(
                "Failed to construct ECDSA public key from coordinates"
            ) from e


@dataclass
class KeyData(DataClassDictMixin):
    """Contains the cryptographic key material and type URL."""

    type_url: str = field(metadata=field_options(alias="typeUrl"))
    value: str  # Base64-encoded serialized protobuf
    key_material_type: str = field(metadata=field_options(alias="keyMaterialType"))

    class Config(BaseConfig):
        serialize_by_alias = True


@dataclass
class KeysetKey(DataClassDictMixin):
    """Represents a single cryptographic key entry in the keyset."""

    key_data: KeyData = field(metadata=field_options(alias="keyData"))
    status: str  # e.g., "ENABLED"
    key_id: int = field(metadata=field_options(alias="keyId"))
    output_prefix_type: str = field(metadata=field_options(alias="outputPrefixType"))

    class Config(BaseConfig):
        serialize_by_alias = True

    @cached_property
    def public_key(self) -> ec.EllipticCurvePublicKey:
        """Loads and returns the standard cryptography EllipticCurvePublicKey from key material.

        Raises:
            KeysetError: If key decoding or construction fails.
        """
        try:
            key_data_bytes = base64.b64decode(self.key_data.value)
        except ValueError as e:
            raise KeysetError("Failed to Base64-decode key value") from e

        return EcdsaPublicKey.deserialize(key_data_bytes)

    def verify(self, signature_bytes: bytes, raw_payload: bytes) -> None:
        """Verify the signature against the raw payload using this key.

        Raises:
            SignatureVerificationError: If verification fails.
        """
        try:
            self.public_key.verify(
                signature_bytes,
                raw_payload,
                ec.ECDSA(hashes.SHA256()),
            )
        except (InvalidSignature, ValueError) as e:
            raise SignatureVerificationError(
                "Signature verification failed: invalid signature"
            ) from e


@dataclass
class _TinkSignature:
    """Represents a parsed Tink-prefixed signature."""

    key_id: int
    signature_bytes: bytes  # ASN.1 DER-encoded signature bytes


@dataclass
class WebhookKeyset(DataClassDictMixin):
    """A Google Tink JSON keyset containing public verification keys."""

    primary_key_id: int = field(metadata=field_options(alias="primaryKeyId"))
    key: list[KeysetKey] = field(default_factory=list)

    class Config(BaseConfig):
        serialize_by_alias = True

    @cached_property
    def _enabled_keys(self) -> dict[int, KeysetKey]:
        """Returns a cached map from key ID to ENABLED KeysetKeys."""
        return {k.key_id: k for k in self.key if k.status == "ENABLED"}

    def verify_signature(self, signature_header: str, raw_payload: bytes) -> None:
        """Verify the webhook signature against the raw payload.

        Args:
            signature_header: The Base64-encoded signature from the
                GOOGLE-HEALTH-API-SIGNATURE HTTP header.
            raw_payload: The raw HTTP request body bytes of the webhook payload.

        Raises:
            ImportError: If the 'cryptography' library is not installed.
            SignatureVerificationError: If the signature is invalid or verification
                fails.
            KeysetError: If the keyset format is invalid or no matching key is
                found.
            ValueError: If the key status is invalid.
        """
        if not _HAS_CRYPTOGRAPHY:
            raise ImportError(
                "The 'cryptography' package is required for signature verification. "
                "Please install google_health_api with the 'security' extra: "
                "pip install google_health_api[security]"
            )

        parsed_sig = self._parse_signature_header(signature_header)

        if (matching_key := self._enabled_keys.get(parsed_sig.key_id)) is None:
            for k in self.key:
                if k.key_id == parsed_sig.key_id:
                    raise KeysetError(
                        f"Key ID {parsed_sig.key_id} is present in keyset but status is {k.status}"
                    )
            raise KeysetError(
                f"No enabled key found in keyset for key ID {parsed_sig.key_id}"
            )

        matching_key.verify(parsed_sig.signature_bytes, raw_payload)

    def _parse_signature_header(self, signature_header: str) -> _TinkSignature:
        """Decodes base64 signature header and extracts key ID and raw signature bytes.

        The signature header format is defined by Google Tink binary format spec:
        - 1-byte version prefix (0x01)
        - 4-byte big-endian key ID
        - The remaining bytes are the actual signature in ASN.1 DER-encoded format
          (which is standard for ECDSA verification in Python's cryptography library).
        """
        try:
            signature_bytes = base64.b64decode(signature_header)
        except ValueError as e:
            raise SignatureVerificationError(
                "Failed to Base64-decode signature header"
            ) from e

        if len(signature_bytes) < 5:
            raise SignatureVerificationError(
                "Signature header is too short (must be at least 5 bytes)"
            )

        key_id = int.from_bytes(signature_bytes[1:5], byteorder="big")
        signature_der = signature_bytes[5:]
        return _TinkSignature(key_id=key_id, signature_bytes=signature_der)
