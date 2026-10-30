# Mubayyin Enterprise Release Governance

**Status:** Implemented in the feature branch as deterministic primitives and tenant-scoped API integration. Not yet merged or deployed.

## Capabilities

1. **Release Evidence Continuity** — immutable System Version Snapshots bind a system configuration hash, component versions, a change manifest and an optional predecessor snapshot hash. Release Records retain their existing evidence hash chain. A material configuration change must be represented by a new system version and an explicit manifest; absence of a manifest is never eligible for automated fast-track.
2. **Risk-Tiered Release Governance** — deterministic classification:
   - Tier 1: routine, explicitly in-boundary changes; automated fast-track may be eligible.
   - Tier 2: material behaviour changes; human review required.
   - Tier 3: consequential components or permission expansion; mandatory human authorization.
   - Tier 4: unknown or out-of-boundary changes; hold.
3. **Enterprise Release Interoperability** — authenticated, tenant-scoped, versioned read API for release records, version snapshots, continuity and risk assessments.

## Fast-track preconditions

Fast-track is eligibility, not deployment authorization. It requires a Tier 1 manifest, evidence completeness, mandatory checks passing, no critical or major findings, a base release status of safe_to_serve, and no policy-mandated human authorization. A passing score alone cannot grant fast-track.

## API

- POST /tenant/systems/{system_id}/version-snapshots
- GET /tenant/systems/{system_id}/version-snapshots
- POST /tenant/releases/{record_id}/risk-assessment
- GET /tenant/releases/{record_id}/risk-assessment
- GET /tenant/releases/{record_id}/continuity
- GET /tenant/integrations/releases/{record_id}

All endpoints require the tenant bearer token. The interoperability endpoint is read-only. It does not deploy, block, retry, reverse or compensate actions.

## Evidence and limitations

SHA-256 fingerprints detect content changes relative to the stored digest; they do not authenticate the issuer or prove the truth of submitted facts. Tenant scoping depends on the existing tenant authentication and PostgreSQL storage. The feature branch requires CI, PostgreSQL restart/readback, cross-tenant, concurrency and security verification before production deployment. No regulatory certification is claimed.
