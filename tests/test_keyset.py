"""Tests for Google Health API webhook keyset parsing and signature verification."""

import base64
import json
from dataclasses import dataclass
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
import pytest

from google_health_api.keyset import (
    KeysetError,
    SignatureVerificationError,
    WebhookKeyset,
)


@dataclass
class KeysetTestContext:
    """Context holding keys, payloads, and signatures for webhook tests."""

    private_key: ec.EllipticCurvePrivateKey
    key_id: int
    keyset_data: dict
    keyset: WebhookKeyset
    payload: bytes
    signature_header: str


@pytest.fixture(name="keyset_ctx")
def fixture_keyset_ctx() -> KeysetTestContext:
    """Generate a cryptographic key pair and Tink keyset for testing."""
    # Generate P-256 key pair
    private_key = ec.generate_private_key(ec.SECP256R1(), default_backend())
    public_key = private_key.public_key()
    public_numbers = public_key.public_numbers()

    x_bytes = public_numbers.x.to_bytes(32, byteorder="big")
    y_bytes = public_numbers.y.to_bytes(32, byteorder="big")

    # Serialize coordinates into a simulated EcdsaPublicKey protobuf message:
    # Field 3 (x): tag 26, length 32
    # Field 4 (y): tag 34, length 32
    protobuf_bytes = b""
    protobuf_bytes += bytes([26, 32]) + x_bytes
    protobuf_bytes += bytes([34, 32]) + y_bytes
    base64_key_val = base64.b64encode(protobuf_bytes).decode("utf-8")

    # Construct keyset structure
    key_id = 987654321
    keyset_data = {
        "primaryKeyId": key_id,
        "key": [
            {
                "keyData": {
                    "typeUrl": "type.googleapis.com/google.crypto.tink.EcdsaPublicKey",
                    "value": base64_key_val,
                    "keyMaterialType": "ASYMMETRIC_PUBLIC",
                },
                "status": "ENABLED",
                "keyId": key_id,
                "outputPrefixType": "TINK",
            }
        ],
    }

    keyset = WebhookKeyset.from_dict(keyset_data)

    payload = b'{"type": "verification"}'
    raw_signature = private_key.sign(payload, ec.ECDSA(hashes.SHA256()))

    # Build full Tink-prefixed signature header: 1-byte version (0x01) + 4-byte keyId
    tink_prefix = b"\x01" + key_id.to_bytes(4, byteorder="big")
    full_signature = tink_prefix + raw_signature
    signature_header = base64.b64encode(full_signature).decode("utf-8")

    return KeysetTestContext(
        private_key=private_key,
        key_id=key_id,
        keyset_data=keyset_data,
        keyset=keyset,
        payload=payload,
        signature_header=signature_header,
    )


def test_verify_signature_success(keyset_ctx: KeysetTestContext) -> None:
    """Verify that a valid signature header correctly validates the payload."""
    keyset_ctx.keyset.verify_signature(keyset_ctx.signature_header, keyset_ctx.payload)


def test_verify_signature_invalid_payload(keyset_ctx: KeysetTestContext) -> None:
    """Verify that signature validation fails if the payload has been modified."""
    with pytest.raises(SignatureVerificationError):
        keyset_ctx.keyset.verify_signature(
            keyset_ctx.signature_header, keyset_ctx.payload + b"modified"
        )


def test_verify_signature_unknown_key_id(keyset_ctx: KeysetTestContext) -> None:
    """Verify that signature validation fails if the key ID in the header is unknown."""
    wrong_key_id = 111111111
    wrong_prefix = b"\x01" + wrong_key_id.to_bytes(4, byteorder="big")
    raw_signature = keyset_ctx.private_key.sign(
        keyset_ctx.payload, ec.ECDSA(hashes.SHA256())
    )
    wrong_signature_header = base64.b64encode(wrong_prefix + raw_signature).decode(
        "utf-8"
    )

    with pytest.raises(KeysetError) as exc_info:
        keyset_ctx.keyset.verify_signature(wrong_signature_header, keyset_ctx.payload)
    assert "No enabled key found in keyset" in str(exc_info.value)


def test_verify_signature_disabled_key(keyset_ctx: KeysetTestContext) -> None:
    """Verify that signature validation fails if the key is present but disabled."""
    disabled_keyset_data = json.loads(json.dumps(keyset_ctx.keyset_data))
    disabled_keyset_data["key"][0]["status"] = "DISABLED"
    disabled_keyset = WebhookKeyset.from_dict(disabled_keyset_data)

    with pytest.raises(KeysetError) as exc_info:
        disabled_keyset.verify_signature(
            keyset_ctx.signature_header, keyset_ctx.payload
        )
    assert "status is DISABLED" in str(exc_info.value)


def test_verify_signature_malformed_header(keyset_ctx: KeysetTestContext) -> None:
    """Verify that signature validation fails if the header value is malformed or too short."""
    too_short_header = base64.b64encode(b"\x01\x02\x03\x04").decode("utf-8")
    with pytest.raises(SignatureVerificationError) as exc_info:
        keyset_ctx.keyset.verify_signature(too_short_header, keyset_ctx.payload)
    assert "too short" in str(exc_info.value)
