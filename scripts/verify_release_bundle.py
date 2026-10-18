#!/usr/bin/env python3
"""Verify a Mubayyin Release Record JSON bundle offline.

Usage:
  python scripts/verify_release_bundle.py path/to/release-bundle.json

Set MUBAYYIN_ATTESTATION_KEY only when you are authorized to verify a
shared-secret HMAC signature. Without the key, a signed bundle's hash can
be checked but its authenticity cannot be verified.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.services.attestation import verify_release_bundle  # noqa: E402


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python scripts/verify_release_bundle.py <bundle.json>", file=sys.stderr)
        return 64
    try:
        bundle = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"valid": False, "status": "input_error", "detail": str(exc)}, indent=2))
        return 2
    if not isinstance(bundle, dict):
        print(json.dumps({"valid": False, "status": "malformed_bundle"}, indent=2))
        return 2
    result = verify_release_bundle(bundle, os.getenv("MUBAYYIN_ATTESTATION_KEY"))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result.get("integrity_valid"):
        return 2
    if result.get("signature_status") == "invalid":
        return 3
    if result.get("signature_status") == "key_unavailable":
        return 4
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
