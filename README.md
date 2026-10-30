# Mubayyin — Release Assurance Lab (pre-production)

This is the smallest real version of the loop in the strategy doc:

```
AISystem  →  ScenarioCase[]  →  TrialResult[]  →  ReleaseRecord
```

## Automated checks

```bash
python3 demo.py
pip install -r requirements.txt
python3 -m unittest discover -s tests -v
```

The demo and core engine use Python's standard library; the HTTP API and full test suite require the packages in `requirements.txt`. GitHub Actions runs the engine/API/public-website tests and a demo end-to-end smoke test. Passing automated tests does not establish production readiness or validate semantic Arabic quality.

What the demo proves:
- A privacy leak and an unauthorized transfer are caught by **deterministic
  checks**, not by asking a model to grade itself.
- A human review record attaches to a finding rather than silently
  overwriting the automated one.
- Any release with an unresolved critical failure becomes `hold_for_repair`,
  and any non-`safe_to_serve` record without a named approver is marked
  provisional.
- Every record carries a `config_hash` (exactly what was tested) and an
  `evidence_hash` (what the result was), so it's reproducible.

## Run locally for a manual integration check

```bash
pip install -r requirements.txt
uvicorn app.api:app --reload
# open http://127.0.0.1:8000/docs
```

This wraps the tested `app/models` and `app/services` code in a FastAPI API. The public sandbox uses a session-scoped cookie and keeps test artifacts in memory only; submitted test text is not persisted. A separate invited-pilot `/tenant/*` API now supports bearer-key authentication, tenant-scoped PostgreSQL evidence, immutable Release Records, human review, key rotation/revocation and durable evidence export. Tenant keys are stored as SHA-256 hashes. PostgreSQL is also used for consented partnership enquiries and opt-in anonymous usage events. The private tenant API still requires a real Railway create → restart → retrieve test before its durability is advertised as production-verified.

Private pilot API, browser workspace (`/workspace`) and security limits: [docs/private-tenant-workspace.md](docs/private-tenant-workspace.md).

## Portable Release Record export and verification

The English and Arabic labs can export a sandbox Release Record as a JSON evidence bundle, including referenced scenario definitions and trial outputs/findings. The canonical SHA-256 payload hash covers both the record and included evidence; optional HMAC-SHA256 signing is available when `MUBAYYIN_ATTESTATION_KEY` is configured.

- API export: `GET /releases/{record_id}/export` (owning sandbox session only)
- API verification: `POST /releases/verify`
- Offline verifier: `python scripts/verify_release_bundle.py <bundle.json>`
- Details and interpretation limits: [docs/release-record-bundle.md](docs/release-record-bundle.md)

An unsigned hash can detect changes to the record and exported evidence but does not authenticate who created the bundle. HMAC is a shared-secret mechanism, not a public-key signature. A valid bundle does not certify AI safety or compliance, and the public sandbox's underlying evidence remains ephemeral.

## Action Mandate Assurance (new feature branch)

A separate deterministic assessment capability evaluates whether a proposed financial-service action matches a versioned Action Mandate. Its original bilingual terminology is documented in [docs/action-mandate-assurance.md](docs/action-mandate-assurance.md). It adds tenant-scoped invited-pilot endpoints for mandate creation, revocation, action assessment and evidence retrieval. It does not execute or block actions; the customer-controlled execution system must enforce decisions. The assessment engine has a dedicated synthetic test suite. This feature is not yet merged into main or deployed.

## Remaining gaps (deliberately staged)

The tenant API is an initial controlled-pilot surface, not a finished enterprise identity product. The following still require validation, security review, or paying pilot evidence:

- Real Railway/PostgreSQL create → restart → retrieve verification, tenant-level audit logging, concurrency/transaction review and security testing
- Real LLM judge (currently a transparent lexical-overlap stand-in in
  `app/services/evaluator.py::reference_judge` — replace with an actual
  model call behind the same `JudgeFn` signature, and add a second,
  independent judge before trusting disagreement checks)
- User-level roles, SSO/MFA, fine-grained reviewer permissions, rate limiting, a production-hardened private workspace UI, CI/CD webhooks, drift watch and SDKs
- Any of the "10 organizations use this scenario library" scale — this
  scaffold ships with 10 illustrative scenarios, not a production library

## Honest next step

Point this at one real (or realistic mocked) customer AI endpoint, load
scenarios drawn from that customer's actual policies and one real
production failure, and see if the Release Record it produces would
actually change someone's release decision. That's Gate 4 from the
strategy doc — everything else waits for it.
