# Mubayyin Release Record Bundle

## What it is

A portable JSON evidence package for one sandbox Release Record. The bundle includes the release decision, the scenario definitions referenced by the record, the underlying trial results (including submitted outputs and findings), and an integrity envelope. Export is available only to the browser session that owns the record; treat the downloaded file as sensitive if you included any non-public text.

- `schema_version`: bundle schema identifier.
- `record`: canonicalized Release Record fields.
- `evidence`: scenario definitions and trial results referenced by that record at export time.
- `integrity.payload_hash_algorithm`: currently `sha256`.
- `integrity.payload_hash`: SHA-256 of canonical JSON containing both `record` and `evidence`.
- `integrity.signature_algorithm` and `integrity.signature`: optional HMAC-SHA256 signature.

The English and Arabic labs expose **Download Release Record bundle** after creating a record. The API route is `GET /releases/{record_id}/export`; export is limited to the browser session that owns that sandbox record.

## Verify through the API

Submit the downloaded bundle JSON as the body of `POST /releases/verify`. The endpoint reports whether the content hash matches and whether any signature could be authenticated.

## Verify offline

From the repository root:

```bash
python scripts/verify_release_bundle.py ./mubayyin-mrr_example.json
```

The CLI uses only Python's standard library plus the repository's own attestation module. It does not need database access.

## Optional HMAC signing

Set `MUBAYYIN_ATTESTATION_KEY` to a strong, random secret in a secured environment before creating bundles. The same secret is required to verify the signature. Keep it out of source control, logs, public client code, and exported bundles. Rotate it under an explicit key-management procedure.

HMAC is a shared-secret mechanism. It is **not** a public-key signature: external parties cannot independently authenticate the signer without access to the shared secret. If no key is configured, bundles are intentionally unsigned.

## Interpret verification honestly

- `integrity_valid_unsigned`: the content matches the hash, but the hash alone does not prove who created the record.
- `integrity_valid_signature_unchecked`: the content hash matches, but the verifier does not have the HMAC key.
- `verified`: the content hash and HMAC both match under the configured shared secret.
- `payload_hash_mismatch` or `signature_invalid`: the bundle must not be treated as verified.

A valid bundle only proves that the exported record and included scenario/trial evidence have not changed relative to the included hash, and—when HMAC is verified—that the bundle was created by someone with the shared key. It does **not** prove the tested AI behaved safely, validate the truth of supplied evidence, establish a chain of custody before export, certify compliance, or make the current in-memory sandbox record durable. The sandbox remains a demonstration and must use synthetic, non-confidential data.
