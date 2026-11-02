# Acceptance Tests — Change, Recovery & Post-Release Validity

**Status:** Proposed test contract for review. These tests are not evidence of implementation or passing behavior.
**Precondition:** Reconcile each case with current API contracts and existing release-governance tests before implementation.

## A. Change classification and independent risk gates

| ID | Scenario | Expected result |
|---|---|---|
| CC-01 | Standard change references active approved policy and stays within its exact bounded scope | Classification may be verified; risk assessment still runs independently |
| CC-02 | Standard change has no policy reference | Classification UNVERIFIED; no automatic fast-track |
| CC-03 | Standard change expands scope beyond policy boundary | Reject or mark classification invalid; require Normal review |
| CC-04 | Emergency change has no urgency reason | Reject validation |
| CC-05 | Emergency change is Tier 4 or has unresolved critical finding | HOLD; urgency cannot lower risk |
| CC-06 | Normal change is Tier 3 | Mandatory human authorization remains required |
| CC-07 | Change category is edited after approval | New immutable revision; prior revision remains auditable |
| CC-08 | Policy version is superseded after classification | Preserve original policy version and flag review according to institution policy |

## B. Change-to-release lineage

| ID | Scenario | Expected result |
|---|---|---|
| CL-01 | Valid change, manifest, snapshot, trials, risk assessment, approval and Release Record are linked | Complete lineage can be retrieved in deterministic order |
| CL-02 | Snapshot config hash differs from manifest target hash | Lineage verification fails closed |
| CL-03 | Release Record references a snapshot from another tenant | Reject without revealing cross-tenant existence |
| CL-04 | Required approval evidence is absent | Release remains provisional / held according to existing policy |
| CL-05 | A lineage event is corrected | Append correction event; do not mutate historical evidence |
| CL-06 | Duplicate mutation request uses same idempotency key and payload | Return original result without duplicate record |
| CL-07 | Same idempotency key is reused with different payload | Reject conflict |

## C. RevertTrace recovery evidence

| ID | Scenario | Expected result |
|---|---|---|
| RT-01 | Prior Release Record, snapshot, hashes and evidence chain are intact | Recovery target may be marked evidence-verified, subject to compatibility |
| RT-02 | Prior version was once SAFE_TO_SERVE but its policy basis is expired | Do not call it currently safe; require reassessment |
| RT-03 | Prior snapshot is missing or hash mismatches | Recovery NOT_VERIFIED |
| RT-04 | Dependency compatibility is unknown | Recovery NOT_VERIFIED / customer review required |
| RT-05 | No prior release exists | Require explicitly documented alternative recovery strategy; no fabricated predecessor |
| RT-06 | Customer reports rollback execution | Store customer-supplied execution evidence; distinguish reported from independently verified |
| RT-07 | Customer reports execution but post-recovery tests fail | Recovery FAILED; preserve all evidence |
| RT-08 | API request attempts to execute rollback through Mubayyin | No execution route exists; reject / route not found |

## D. ValidityWatch and point-in-time boundary

| ID | Scenario | Expected result |
|---|---|---|
| VW-01 | Customer submits valid signal referencing the exact release | Signal is stored with observed/received timestamps and source metadata |
| VW-02 | Signal references another tenant's release | Reject without cross-tenant disclosure |
| VW-03 | Signal is stale beyond configured freshness window | VALIDITY_EXPIRED or UNVERIFIED, never CURRENT |
| VW-04 | Signal lacks trusted source / issuer proof | Mark UNVERIFIED; do not treat as authenticated |
| VW-05 | Configured threshold is breached | REASSESSMENT_REQUIRED; do not silently rewrite prior Release Record |
| VW-06 | Material configuration change occurs after release | Mark prior point-in-time decision as no longer covering the changed configuration |
| VW-07 | No monitoring feed is connected | State monitoring evidence unavailable / unassessed, not healthy |
| VW-08 | Customer reports suspension | Record CUSTOMER_SUSPENSION_REPORTED; do not claim Mubayyin suspended system |
| VW-09 | Out-of-order signals arrive | Preserve event time and receipt time; apply deterministic ordering / conflict policy |
| VW-10 | Duplicate signal ID or source event ID is submitted | Idempotent behavior; no duplicate state transition |

## E. Regulatory evidence mapping

| ID | Scenario | Expected result |
|---|---|---|
| RM-01 | Customer maps a Release Record to a named control and version | Store mapping and linked evidence references |
| RM-02 | Mapping has no source/version or applicability rationale | Mark incomplete / reject acceptance |
| RM-03 | Customer labels one mapping "NCA Compliant" | Store only as customer assertion if policy allows; UI must not present as Mubayyin certification |
| RM-04 | Evidence reference is absent or belongs to another tenant | Mapping remains incomplete / reject cross-tenant reference |
| RM-05 | Control framework version changes | Preserve historical mapping and require explicit remapping/review |
| RM-06 | Control marked NOT_APPLICABLE | Require rationale and named customer reviewer |

## F. Security, privacy and resilience

| ID | Scenario | Expected result |
|---|---|---|
| SR-01 | Tenant A requests any ChangeClass, RevertTrace, signal or mapping owned by Tenant B | Consistent 404/authorization policy with no data leakage |
| SR-02 | Concurrent approvals or classifications target same revision | Transaction-safe conflict handling; no lost update |
| SR-03 | Database transaction fails midway through multi-record lineage write | Full rollback or recoverable explicit partial state; no false complete lineage |
| SR-04 | Oversized or malformed payload submitted | Bounded validation error; no process crash |
| SR-05 | Signature invalid or key revoked | Evidence marked unauthenticated/rejected under policy |
| SR-06 | Database restart after writes | Records remain retrievable and hashes verify |
| SR-07 | Backup restored to isolated environment | Restore verification and evidence-chain integrity report |
| SR-08 | Sensitive payload fields are submitted | Minimize, redact or reject according to retention policy |
| SR-09 | Authorization changes after approval | Historical approval remains recorded; current authorization state is explicit |
| SR-10 | Audit export is generated | Export includes stable identifiers, event order, source metadata and integrity verification instructions |

## G. Release gates

A feature is not eligible for production until:
1. Unit and API tests pass.
2. PostgreSQL integration tests pass.
3. Tenant isolation tests pass for every new entity and relationship.
4. Restart/readback and backup/restore tests pass.
5. Concurrency, idempotency and transaction tests pass.
6. Threat model and security review are completed.
7. Retention/deletion and audit semantics are documented.
8. OpenAPI contracts and customer documentation match actual behavior.
9. Deployment verification confirms the exact commit and migration state.
10. Product claims and UI labels accurately distinguish verified, customer-reported, unverified and unavailable evidence.

## H. Review questions for independent reviewer

1. Is the separation between change category and risk tier sufficiently fail-closed?
2. Are the proposed immutable revision and correction semantics sound?
3. What minimum issuer-authentication model is required before external approvals/signals are trusted?
4. Does RevertTrace prove only plan readiness, or is any wording implying operational rollback?
5. Are freshness windows and post-release validity states sufficiently explicit?
6. Which regulatory mapping labels could mislead an auditor or buyer?
7. Which acceptance cases are missing for multi-tenant concurrency and partial failure?
8. What should be rejected from the first implementation to keep scope small?
