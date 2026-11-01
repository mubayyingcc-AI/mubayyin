# Five-workstream implementation — research prototype

This implementation adds deterministic, dependency-free primitives for the five workstreams defined in `docs/qstp-phased-rd-architecture.md`.

## Modules

- `app/services/assurance_workstreams.py`
  - WP1: Arabic text normalisation and literal/phrase financial checks.
  - WP2: SHA-256 canonical evidence manifest with HMAC-SHA256 integrity/authenticity check.
  - WP3: scenario-severity baseline/candidate comparison.
  - WP4: fail-closed decision function with explicit evidence, threshold, regression and human-approval gates.
  - WP5: deterministic retest event and idempotency-key contract.
  - Integrated orchestration function connecting WP1–WP4 and exposing the WP5 event contract.

## Run tests

```bash
python3 -m unittest tests.test_assurance_workstreams -v
python3 -m unittest discover -s tests -v
```

## Explicit limitations

- WP1 is not semantic Arabic evaluation; it does not claim dialect comprehension or meaning correctness.
- WP2 uses HMAC shared-secret signing. It is not asymmetric signing, non-repudiation or independent identity verification. Production key custody and rotation remain separate work.
- WP3 compares supplied severity labels; it does not prove causality or statistical significance.
- WP4 is a technical policy aid; institutional release authority remains with the customer.
- WP5 defines an event contract only. It does not persist or dispatch events, and must be connected to a durable tenant-scoped queue before operational use.
- The integrated function is not yet wired into customer tenant endpoints or the production website. It must pass integration, security and tenant-boundary review before exposure.

No customer data, secrets, model-provider calls or production database changes are introduced.
