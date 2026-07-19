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
"""

import base64
from dataclasses import dataclass, field

from mashumaro import DataClassDictMixin, field_options
from mashumaro.config import BaseConfig

from ._protobuf import (
    TYPE_BIG_ENDIAN_INT,
    TYPE_UINT32,
    ProtobufParseError,
    deserialize_protobuf,
)


try:
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import ec

    _HAS_CRYPTOGRAPHY = True
except ImportError:
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

    x: int = field(metadata={"field_number": 3, "proto_type": TYPE_BIG_ENDIAN_INT})
    y: int = field(metadata={"field_number": 4, "proto_type": TYPE_BIG_ENDIAN_INT})
    version: int = field(
        metadata={"field_number": 1, "proto_type": TYPE_UINT32}, default=0
    )

    @classmethod
    def deserialize(cls, data: bytes) -> "EcdsaPublicKey":
        """Deserialize from binary serialized Protobuf bytes.

        Raises:
            KeysetError: If parsing fails due to [ProtobufParseError](file:///Users/allen/.gemini/antigravity/worktrees/python-google-health-api/review-webhook-signature-implementation/google_health_api/_protobuf.py#L11)
                or truncated data (which raises an [IndexError]).
        """
        try:
            return deserialize_protobuf(cls, data)
        except (ProtobufParseError, IndexError) as e:
            raise KeysetError("Failed to parse key protobuf data") from e


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


@dataclass
class WebhookKeyset(DataClassDictMixin):
    """A Google Tink JSON keyset containing public verification keys."""

    primary_key_id: int = field(metadata=field_options(alias="primaryKeyId"))
    key: list[KeysetKey] = field(default_factory=list)

    class Config(BaseConfig):
        serialize_by_alias = True

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
        """
        if not _HAS_CRYPTOGRAPHY:
            raise ImportError(
                "The 'cryptography' package is required for signature verification. "
                "Please install google_health_api with the 'security' extra: "
                "pip install google_health_api[security]"
            )

        try:
            signature_bytes = base64.b64decode(signature_header)
        except Exception as e:
            raise SignatureVerificationError(
                "Failed to Base64-decode signature header"
            ) from e

        if len(signature_bytes) < 5:
            raise SignatureVerificationError(
                "Signature header is too short (must be at least 5 bytes)"
            )

        # Tink's output prefix is 5 bytes: 1-byte version (usually 0x01) + 4-byte keyId
        _version = signature_bytes[0]
        key_id = int.from_bytes(signature_bytes[1:5], byteorder="big")
        signature_der = signature_bytes[5:]

        # Find matching ENABLED key in the keyset
        matching_key = None
        for k in self.key:
            if k.key_id == key_id:
                if k.status == "ENABLED":
                    matching_key = k
                    break
                else:
                    raise KeysetError(
                        f"Key ID {key_id} is present in keyset but status is {k.status}"
                    )

        if not matching_key:
            raise KeysetError(f"No enabled key found in keyset for key ID {key_id}")

        # Parse coordinates from Tink protobuf wrapper
        try:
            key_data_bytes = base64.b64decode(matching_key.key_data.value)
        except Exception as e:
            raise KeysetError("Failed to Base64-decode key value") from e

        public_key_proto = EcdsaPublicKey.deserialize(key_data_bytes)

        # Load key coordinates and verify signature
        try:
            public_numbers = ec.EllipticCurvePublicNumbers(
                x=public_key_proto.x,
                y=public_key_proto.y,
                curve=ec.SECP256R1(),
            )
            public_key = public_numbers.public_key()
        except Exception as e:
            raise KeysetError(
                "Failed to construct ECDSA public key from coordinates"
            ) from e

        try:
            public_key.verify(signature_der, raw_payload, ec.ECDSA(hashes.SHA256()))
        except Exception as e:
            raise SignatureVerificationError(
                "Signature verification failed: invalid signature"
            ) from e
