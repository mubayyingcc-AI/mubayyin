# Tenant API integration for five assurance workstreams

The router in `app/routers/assurance.py` is registered by `app/api.py` under the existing FastAPI application.

## Authenticated endpoints

All endpoints require the existing tenant bearer token and resolve system records within that tenant.

- `POST /tenant/assurance/assessments`
  - Runs the five-workstream research assessment against an existing tenant system.
  - Binds the immutable assessment to the system's current configuration hash and policy version.
  - Persists the result as `rd_assessment` using the existing tenant evidence store.
  - Deliberately forces `evidence_complete=false`: the request cannot self-assert evidence completeness, so the research decision remains fail-closed.
  - Does not create, update or approve a Release Record.

- `GET /tenant/assurance/assessments/{assessment_id}`
  - Reads the immutable assessment through tenant-scoped storage.

- `POST /tenant/assurance/retests`
  - Requires the submitted current snapshot hash to match the tenant system's current configuration hash.
  - Persists an immutable, tenant-scoped retest event with an idempotency key.
  - Event status is `recorded_not_dispatched`; no worker, queue or automatic retest is claimed.

- `GET /tenant/assurance/retests`
  - Lists retest events belonging only to the authenticated tenant.

## Safety and limitations

- No public or unauthenticated endpoint is added.
- No tenant identifier is accepted from the caller as an authority claim; it is derived from bearer-token authentication.
- The system identity and configuration hash are resolved from the authenticated tenant's durable records.
- Research assessment and retest records use the existing immutable evidence-store insertion path.
- The API currently does not provision a signing key or persist HMAC signatures; evidence-manifest signing remains an explicit integration gap until controlled key management is configured.
- The bilingual evaluator remains literal/phrase-based, not semantic Arabic evaluation.
- Behaviour comparison consumes supplied baseline/candidate severity labels; it is not a substitute for a validated regression benchmark.
- Retest events are durable records only and are not automatically dispatched.
- These endpoints do not change the existing release decision path and do not confer regulatory certification.

## Manual smoke-test sequence

1. Provision or use an existing tenant and bearer token.
2. Create a tenant system using `POST /tenant/systems`.
3. Run `POST /tenant/assurance/assessments` with that system ID and synthetic output.
4. Confirm the response identifies the same system configuration hash and returns durable persistence.
5. Fetch the assessment using its ID and confirm identical content.
6. Submit a retest event with the exact current system configuration hash.
7. Fetch the retest list and confirm the event appears once.
8. Repeat the same retest request and confirm the duplicate/idempotency response.
9. Attempt to fetch either record with another tenant token and confirm it is not disclosed.
10. Confirm that no Release Record was created by these research endpoints.

Use only synthetic data for these checks. Production deployment remains gated on a dedicated endpoint integration test against disposable PostgreSQL, security review, and confirmation of the full existing test suite.
