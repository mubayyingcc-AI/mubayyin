# Mubayyin Private Tenant Workspace API (Pilot)

## Purpose and boundary

The public `/systems`, `/scenarios`, `/trials`, and `/releases` routes are an ephemeral demonstration sandbox. The `/tenant/*` routes are a separate API path for invited pilot organizations that need PostgreSQL-backed evidence. They require a tenant API key on every request and read/write evidence scoped to that tenant ID. Tenant records are loaded from the database per request, so retrieval does not depend on the public sandbox's in-memory maps.

**This is a controlled pilot API, not yet a production SaaS identity system.** Use HTTPS, keep admin and tenant keys in a secret manager, restrict who receives keys, and do not submit production customer data until the security/privacy review and contractual controls are complete. The current evaluator limitations still apply.

## Required configuration

- `DATABASE_URL`: PostgreSQL connection string. Tenant provisioning and tenant evidence endpoints fail closed if database storage is unavailable.
- `MUBAYYIN_TENANT_ADMIN_TOKEN`: dedicated administrator secret for tenant provisioning, key rotation and revocation. This is separate from `PARTNER_ADMIN_TOKEN`.
- Optional `MUBAYYIN_ATTESTATION_KEY`: shared HMAC key for signed Release Record bundles. If unset, bundles are unsigned and only content integrity can be checked.

## Provision a tenant

An administrator calls `POST /admin/tenants` with `Authorization: Bearer <MUBAYYIN_TENANT_ADMIN_TOKEN>` and JSON such as `{"name":"Pilot Organisation"}`. The response contains a randomly generated tenant API key **once**. The database stores only its SHA-256 hash. Copy the key into a secret manager; it cannot be retrieved from the database later.

Rotate a key with `POST /admin/tenants/{tenant_id}/rotate-key`. Revoke access with `POST /admin/tenants/{tenant_id}/revoke`. Revocation preserves the tenant's evidence rows but blocks that key and any future use of the tenant credentials. Rotation invalidates the previous key immediately.

## Pilot workflow

Use `Authorization: Bearer <tenant-api-key>` on every `/tenant/*` request:

1. `GET /tenant/me` — verify tenant identity and durable-storage mode.
2. `POST /tenant/systems` — register a versioned system configuration.
3. `POST /tenant/scenarios` — register a scenario and its explicit expected/forbidden behaviour.
4. `POST /tenant/trials` — run the current deterministic/reference evaluator and save the result durably.
5. `POST /tenant/trials/{result_id}/review` — record a human review before release; reviews are rejected after the trial is included in a Release Record.
6. `POST /tenant/releases` — create an immutable Release Record with required scenario coverage and configured thresholds.
7. `GET /tenant/releases/{record_id}` — retrieve the stored record after any process restart.
8. `GET /tenant/releases/{record_id}/export` — export the Release Record plus referenced scenario definitions and trial evidence as a verifiable JSON bundle.
9. `POST /releases/verify` — verify the exported bundle's content hash and, when the HMAC key is configured, its signature.

The interactive API docs are available at `/docs` on the deployed service; use its Authorize control to provide the tenant bearer token. Do not paste tenant keys into public screenshots, issue reports or browser scripts that may be shared.

## What the controls do—and do not—guarantee

- Tenant API keys are stored as SHA-256 hashes, not plaintext. They are bearer credentials: anyone holding a key can act as that tenant until rotation or revocation.
- Database queries for tenant evidence include the authenticated tenant ID. Cross-tenant reads should return not found rather than reveal another tenant's record.
- Release Records are inserted as immutable rows; trials cannot be reviewed after a Release Record references them.
- A database-backed record is durable across application restarts, but this API still needs a real Railway create → restart → retrieve integration test before it is advertised to design partners as verified.
- The API does not yet provide user-level roles, SSO, MFA, fine-grained reviewer permissions, tenant audit logs, rate limiting, a self-service browser workspace, or a public-key signing infrastructure. Tenant keys are shared within each organization until those controls are built.
- The reference evaluator does not perform semantic Arabic assessment or certify safety/compliance. A durable Release Record is an evidence artifact, not a guarantee that the AI system is safe.
