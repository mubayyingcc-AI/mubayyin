"""Portable Mubayyin Release Record bundles with explicit integrity/authenticity semantics.

SHA-256 detects changes to the exported record. An optional HMAC-SHA256 signature
authenticates the bundle only to parties holding the shared secret. Unsigned hashes
are not digital signatures and do not prove who created a record.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
from typing import Any

SCHEMA_VERSION = "mubayyin.release-bundle.v1"


def canonical_json(value: Any) -> bytes:
    """Serialize JSON deterministically for hashing/signing."""
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def create_release_bundle(record: dict[str, Any], signing_key: str | None = None) -> dict[str, Any]:
    """Create an integrity-checked export; sign only when a key is configured."""
    payload = dict(record)
    payload.pop("persistence", None)
    digest = hashlib.sha256(canonical_json(payload)).hexdigest()
    key = signing_key if signing_key is not None else os.getenv("MUBAYYIN_ATTESTATION_KEY", "")
    signature = hmac.new(key.encode("utf-8"), digest.encode("ascii"), hashlib.sha256).hexdigest() if key else None
    return {
        "schema_version": SCHEMA_VERSION,
        "record": payload,
        "integrity": {
            "payload_hash_algorithm": "sha256",
            "payload_hash": digest,
            "signature_algorithm": "hmac-sha256" if key else "none",
            "signature": signature,
        },
    }


def verify_release_bundle(bundle: dict[str, Any], signing_key: str | None = None) -> dict[str, Any]:
    """Verify bundle structure and content hash, then verify HMAC if possible."""
    if not isinstance(bundle, dict) or bundle.get("schema_version") != SCHEMA_VERSION:
        return _invalid("unsupported_schema", "Unsupported or missing bundle schema.")
    record = bundle.get("record")
    integrity = bundle.get("integrity")
    if not isinstance(record, dict) or not isinstance(integrity, dict):
        return _invalid("malformed_bundle", "Bundle must contain a record object and integrity object.")
    if integrity.get("payload_hash_algorithm") != "sha256":
        return _invalid("unsupported_hash_algorithm", "Only SHA-256 payload hashes are supported.")
    supplied_hash = integrity.get("payload_hash")
    if not isinstance(supplied_hash, str) or len(supplied_hash) != 64:
        return _invalid("malformed_hash", "Payload hash must be a 64-character SHA-256 hex digest.")
    try:
        computed_hash = hashlib.sha256(canonical_json(record)).hexdigest()
    except (TypeError, ValueError):
        return _invalid("malformed_record", "Record cannot be serialized as canonical JSON.")
    hash_valid = hmac.compare_digest(computed_hash, supplied_hash.lower())
    if not hash_valid:
        return {
            "valid": False, "integrity_valid": False, "authenticity_verified": False,
            "status": "payload_hash_mismatch", "signature_status": "not_checked",
            "computed_payload_hash": computed_hash,
            "limitations": "The record differs from the payload covered by the supplied hash.",
        }

    algorithm = integrity.get("signature_algorithm", "none")
    signature = integrity.get("signature")
    key = signing_key if signing_key is not None else os.getenv("MUBAYYIN_ATTESTATION_KEY", "")
    if algorithm == "none" and not signature:
        return {
            "valid": True, "integrity_valid": True, "authenticity_verified": False,
            "status": "integrity_valid_unsigned", "signature_status": "unsigned",
            "computed_payload_hash": computed_hash,
            "limitations": "The hash detects content changes but does not authenticate who created the record.",
        }
    if algorithm != "hmac-sha256" or not isinstance(signature, str):
        return _invalid("unsupported_signature", "Signature metadata is malformed or uses an unsupported algorithm.")
    if not key:
        return {
            "valid": True, "integrity_valid": True, "authenticity_verified": False,
            "status": "integrity_valid_signature_unchecked", "signature_status": "key_unavailable",
            "computed_payload_hash": computed_hash,
            "limitations": "Payload integrity is valid, but authenticity cannot be verified without the configured HMAC key.",
        }
    expected = hmac.new(key.encode("utf-8"), computed_hash.encode("ascii"), hashlib.sha256).hexdigest()
    signature_valid = hmac.compare_digest(expected, signature)
    return {
        "valid": hash_valid and signature_valid,
        "integrity_valid": hash_valid,
        "authenticity_verified": signature_valid,
        "status": "verified" if signature_valid else "signature_invalid",
        "signature_status": "valid" if signature_valid else "invalid",
        "computed_payload_hash": computed_hash,
        "limitations": "HMAC authenticity is shared-secret verification, not a public-key signature or independent third-party certification.",
    }


def _invalid(status: str, message: str) -> dict[str, Any]:
    return {
        "valid": False, "integrity_valid": False, "authenticity_verified": False,
        "status": status, "signature_status": "not_checked", "limitations": message,
    }
