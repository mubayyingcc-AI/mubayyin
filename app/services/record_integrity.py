"""Canonical Release Record integrity envelopes.

A digest detects changes relative to a known bundle. An HMAC authenticates
the bundle only when the verification party trusts the secret key owner.
Neither mechanism proves that the underlying AI behavior is safe.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
from typing import Any


def canonical_json(value: Any) -> bytes:
    """Serialize JSON deterministically for hashing/signing."""
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def record_digest(record: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json(record)).hexdigest()


def create_attestation(record: dict[str, Any]) -> dict[str, Any]:
    """Create a digest envelope and optional HMAC signature."""
    digest = record_digest(record)
    key = os.getenv("MUBAYYIN_RECORD_SIGNING_KEY", "")
    key_id = os.getenv("MUBAYYIN_RECORD_SIGNING_KEY_ID", "default")
    signature = None
    if key:
        signature = {
            "algorithm": "HMAC-SHA256",
            "key_id": key_id,
            "value": hmac.new(key.encode("utf-8"), canonical_json(record), hashlib.sha256).hexdigest(),
        }
    return {
        "schema_version": "mubayyin-release-envelope-v1",
        "record": record,
        "record_digest": digest,
        "signature": signature,
    }


def verify_attestation(bundle: dict[str, Any]) -> dict[str, Any]:
    """Verify digest integrity and, when possible, the optional HMAC."""
    record = bundle.get("record")
    if not isinstance(record, dict):
        return {"valid": False, "digest_valid": False, "signature_status": "not_checked", "reason": "record_missing_or_invalid"}
    try:
        actual_digest = record_digest(record)
    except (TypeError, ValueError):
        return {"valid": False, "digest_valid": False, "signature_status": "not_checked", "reason": "record_not_canonical_json"}
    digest_valid = hmac.compare_digest(str(bundle.get("record_digest", "")), actual_digest)
    signature = bundle.get("signature")
    if not digest_valid:
        return {"valid": False, "digest_valid": False, "signature_status": "not_checked", "reason": "record_digest_mismatch"}
    if signature is None:
        return {"valid": True, "digest_valid": True, "signature_status": "unsigned", "reason": "digest_only_no_authenticity_claim"}
    if not isinstance(signature, dict) or signature.get("algorithm") != "HMAC-SHA256":
        return {"valid": False, "digest_valid": True, "signature_status": "unsupported", "reason": "signature_format_unsupported"}
    key = os.getenv("MUBAYYIN_RECORD_SIGNING_KEY", "")
    expected_key_id = os.getenv("MUBAYYIN_RECORD_SIGNING_KEY_ID", "default")
    if not key:
        return {"valid": True, "digest_valid": True, "signature_status": "unverifiable_no_server_key", "reason": "digest_valid_but_signature_cannot_be_verified_here"}
    if signature.get("key_id") != expected_key_id:
        return {"valid": False, "digest_valid": True, "signature_status": "key_id_mismatch", "reason": "signing_key_id_not_recognized"}
    expected = hmac.new(key.encode("utf-8"), canonical_json(record), hashlib.sha256).hexdigest()
    signature_valid = hmac.compare_digest(str(signature.get("value", "")), expected)
    return {
        "valid": signature_valid,
        "digest_valid": True,
        "signature_status": "valid" if signature_valid else "invalid",
        "reason": "signature_valid" if signature_valid else "signature_mismatch",
    }
