# Enterprise Change, Recovery & Post-Release Validity Architecture

**Status:** Design proposal for independent technical review. Not implemented, not merged, and not deployed.
**Product:** Mubayyin Release Assurance
**Owner:** Mubayyin AI Technology
**Review audience:** Enterprise architecture, CIO/ITSM, AI governance, internal audit, security and engineering.

## 1. Purpose

Extend Mubayyin's release-assurance evidence model so institutions can connect an AI-system change to its classification, tested configuration, release decision, recovery plan and post-release validity evidence.

The extension must preserve Mubayyin's product boundary:

- Mubayyin assesses evidence, applies configured policy, records decisions and exposes verifiable evidence.
- The customer remains authoritative for change approval, deployment, production monitoring, rollback execution and regulatory interpretation.
- Mubayyin does not independently deploy, block, rollback, retry, compensate or operate a production AI system.

## 2. Existing foundation vs proposed work

### Existing foundation (verify against current main before implementation)

- Tenant-scoped system records and version snapshots.
- Configuration fingerprints and change manifests.
- Risk assessment tiers 1–4.
- Release Records and evidence-hash predecessor continuity.
- Human review / approval evidence and read-only interoperability concepts.
- Customer-controlled runner direction.

The exact production availability and operational assurance of each item must be confirmed from the deployed commit and live tests. A CI pass is not proof of production durability.

### Proposed components in this document

| Component | Responsibility | Status |
|---|---|---|
| ChangeClass | Organization-configurable Standard / Normal / Emergency classification | Proposed |
| ChangeLineage | Link change request, manifest, snapshot, tests, approvals and Release Record | Proposed extension |
| RevertTrace | Record prior known-good version and evidence-backed recovery plan | Proposed |
| ValidityWatch | Ingest customer-supplied post-release signals and assess freshness / reassessment need | Proposed |
| RegMap | Attach organization policy and regulatory control references to evidence | Proposed |

No API, database table, UI, integration or automated behavior described below should be represented as implemented until separately built and tested.

## 3. Two-axis governance model

Change classification and Mubayyin risk tier are independent dimensions.

### Change classification

- **Standard:** A pre-authorized, repeatable, bounded change type whose exact scope and acceptance conditions are governed by an institution's approved policy.
- **Normal:** A planned change requiring the institution's defined assessment and approval path.
- **Emergency:** An expedited change path for urgent circumstances, still subject to evidence, authorization and post-change review.

Mubayyin stores the classification and the policy source/version that assigned it. The customer owns classification policy and CAB process.

### Mubayyin risk tier

Retain the existing risk assessment semantics:

- Tier 1: bounded routine change; fast-track may be eligible if every precondition passes.
- Tier 2: material behavior change; human review required.
- Tier 3: consequential component / permission expansion; mandatory human authorization.
- Tier 4: unknown, out-of-boundary or insufficient evidence; hold.

**Non-negotiable rule:** Change category never lowers, overrides or substitutes for risk tier, findings, evidence completeness or mandatory authorization. An Emergency change may still be Tier 4 / HOLD. A Standard change is not automatically SAFE_TO_SERVE.

### Decision composition

The final decision is the strictest applicable outcome across:
1. risk tier;
2. mandatory policy gates;
3. test findings and evidence completeness;
4. required human authorization;
5. snapshot and lineage integrity;
6. recovery readiness where policy requires it.

No score or category alone grants release eligibility.

## 4. Component specifications

### 4.1 ChangeClass

Required record fields:
- change_id (tenant-scoped immutable identifier)
- system_id
- requested_by / created_at
- classification: STANDARD | NORMAL | EMERGENCY
- classification_reason
- policy_id and policy_version
- scope_summary and affected_components
- urgency_reason (required for EMERGENCY)
- related_change_reference (optional external ticket ID)
- classification_evidence_hash
- status: DRAFT | SUBMITTED | REVIEWED | CLOSED

Validation:
- STANDARD requires a matching active pre-authorized policy and bounded scope.
- EMERGENCY requires a reason and designated customer authorization evidence.
- Missing or stale policy reference makes classification unverified; it does not default to STANDARD.
- Classification edits create a new immutable revision; no silent overwrite.

### 4.2 ChangeLineage

Connect the following evidence identities:
- Change record and policy version
- Change manifest
- System Version Snapshot and config fingerprint
- Scenario set and trial evidence
- Risk assessment
- Human review / approval evidence
- Release Record and evidence hash
- deployment reference supplied by customer (optional)
- post-release validity evidence (when available)

Lineage is append-only. Corrections are new events referencing the superseded event. The chain must distinguish evidence existence from evidence truth and issuer authenticity.

### 4.3 RevertTrace

Purpose: demonstrate that a customer has a defined, evidence-backed recovery path if a released version becomes invalid.

Required fields:
- recovery_plan_id, tenant_id, system_id
- target_release_record_id
- prior_release_record_id (required when a prior release exists)
- prior_snapshot_id and prior_config_hash
- target_snapshot_id and target_config_hash
- dependency / compatibility manifest
- recovery_trigger_policy_id and policy_version
- preconditions and known limitations
- data/state compatibility assessment
- customer execution owner / role reference
- approval reference and timestamp
- verification test references proving the prior version remains eligible
- status: DRAFT | REVIEWED | AUTHORIZED_BY_CUSTOMER | EXECUTION_REPORTED | VERIFIED | FAILED | SUPERSEDED
- execution evidence supplied by customer, if executed

Rules:
- Never infer that a prior version is safe merely because it was previously released.
- A recovery target must have its own intact Release Record, snapshot, evidence chain and still-valid policy basis.
- If prior evidence is missing, broken, stale or incompatible, mark recovery NOT_VERIFIED and require customer review.
- Mubayyin records and assesses; customer executes rollback.
- Do not label a recovery plan as rollback capability until end-to-end customer execution has been independently demonstrated.

### 4.4 ValidityWatch

Purpose: model the post-release assurance boundary without claiming to be a general production observability system.

Accepted customer-supplied signal envelope:
- signal_id, tenant_id, system_id, release_record_id
- observed_at and received_at
- source_system and source_event_id
- signal_type: POLICY_VIOLATION | QUALITY_REGRESSION | SAFETY_INCIDENT | DRIFT_INDICATOR | CONFIG_CHANGE | DEPENDENCY_CHANGE | CONTROL_FAILURE | OTHER
- severity and customer-defined threshold reference
- metric / finding references (avoid raw sensitive payloads)
- evidence_digest and issuer identity metadata
- signature / authentication verification result, if supported by a trusted integration
- retention classification

Validity state:
- VALIDITY_UNASSESSED
- VALIDITY_CURRENT
- REASSESSMENT_REQUIRED
- VALIDITY_EXPIRED
- VALIDITY_UNVERIFIED
- CUSTOMER_SUSPENSION_REPORTED

Rules:
- A release decision is point-in-time and must show its evaluation timestamp, policy version and evidence freshness.
- A signal does not automatically revoke or change a Release Record.
- Configured threshold breaches or material configuration/dependency changes can trigger REASSESSMENT_REQUIRED.
- Missing, unauthenticated or stale signal feeds must be visible as UNKNOWN / UNVERIFIED, never interpreted as healthy.
- Customer retains authority to suspend, disable, rollback or continue service.
- Initial implementation should support manual/API evidence submission. Streaming connectors and automated monitoring are later work.

### 4.5 RegMap

Purpose: attach control references and evidence mappings to Release Records without making a legal or regulatory compliance determination.

Fields:
- mapping_id, tenant_id, release_record_id
- framework_name and framework_version
- jurisdiction
- control_reference and customer-provided control_title
- applicability: APPLICABLE | NOT_APPLICABLE | UNDER_REVIEW
- applicability_rationale
- evidence_reference_ids
- mapping_owner / reviewer
- assessed_at and next_review_at
- mapping_status: DRAFT | REVIEWED | ACCEPTED_BY_CUSTOMER | SUPERSEDED

Rules:
- Support institution-defined control libraries and references such as applicable NCA requirements or SDAIA-related governance materials only after exact source/version is identified.
- Never generate a blanket label such as "NCA Compliant" or "SDAIA Approved" from the presence of a mapping.
- Distinguish mapped, evidence-attached, customer-reviewed and independently assessed.
- Regulatory interpretation and applicability remain with the institution and its advisers.

## 5. Evidence integrity and trust model

- Continue using canonical serialization and SHA-256 digests for tamper detection / content identity.
- Hashes alone do not authenticate the author, source system, timestamp or truth of evidence.
- Before accepting external approvals or signals as authenticated, define issuer identity, key custody, signature verification, revocation, rotation, timestamp trust and audit policy.
- Use tenant-scoped authorization for every read and write; never trust tenant_id supplied in request body without deriving access scope from authenticated principal.
- Append-only event semantics; correction events reference prior event IDs and digests.
- Idempotency keys are required before retryable mutation endpoints are exposed to automation.
- Avoid storing raw customer prompts, personal data, secrets or full production telemetry unless a documented purpose, minimization, retention and deletion policy permits it.

## 6. Proposed API contracts (illustrative; not implemented)

All routes below are proposals and must be reconciled with existing naming, auth and storage conventions before code is written.

- POST /tenant/changes
- GET /tenant/changes/{change_id}
- POST /tenant/changes/{change_id}/classifications
- POST /tenant/changes/{change_id}/lineage-links
- POST /tenant/releases/{release_id}/recovery-plans
- GET /tenant/releases/{release_id}/recovery-plans
- POST /tenant/releases/{release_id}/validity-signals
- GET /tenant/releases/{release_id}/validity
- POST /tenant/releases/{release_id}/control-mappings
- GET /tenant/releases/{release_id}/control-mappings

All responses should expose stable IDs, timestamps, policy versions, evidence references, verification state and explicit limitations. Read APIs should be versioned and tenant-scoped. Mutation APIs must reject cross-tenant references and support idempotency before automation.

## 7. Integration strategy

API-first, but no vendor-specific integration is required for the first increment.

Potential future adapters:
- Azure DevOps / GitHub Actions: change and deployment references.
- Microsoft Purview: data governance / classification references.
- Azure AI Foundry: model and deployment metadata.
- Customer SIEM / monitoring / incident systems: post-release signals.

Adapters must be opt-in, least-privilege, read-only where possible and customer-controlled. Do not store customer credentials in Mubayyin for the first implementation. Do not imply any of these integrations currently exist.

## 8. Security, privacy and operational boundaries

- Tenant isolation applies to every entity and every evidence edge.
- Authorization must be role-aware before enterprise rollout; tenant bearer keys alone are not a complete enterprise identity model.
- Audit who created, classified, reviewed, approved, mapped and superseded each record.
- Rate-limit and bound payload size; validate schema and timestamps.
- Prevent replay, duplicate mutation and out-of-order evidence from silently changing state.
- Establish retention, deletion, export and backup/restore controls.
- Test database transactions and concurrent updates.
- Define incident response, key rotation/revocation and recovery procedures.
- Do not process real customer production data until security, privacy, contractual and operational controls are approved.

## 9. Delivery phases

### Phase A — Specification and review
Freeze terminology, state transitions, schemas, API contracts and acceptance tests. Obtain independent technical review. No production changes.

### Phase B — Minimal evidence model
Implement ChangeClass and ChangeLineage as append-only tenant-scoped records. Add migrations, API schemas, audit events and tests. No CI/CD adapters.

### Phase C — Recovery evidence
Implement RevertTrace as a documented assessment and evidence record. No rollback execution.

### Phase D — Post-release validity
Implement manual/API signal ingestion, freshness states and reassessment flags. No live monitoring claims.

### Phase E — Control mapping
Implement customer-owned control references and evidence mapping. No compliance certification claims.

### Phase F — Integrations
Only after demand and threat review, add least-privilege adapters for selected customer systems.

## 10. Explicit non-goals

- Replacing ITSM, CAB, MLOps, CI/CD, SIEM or data governance platforms.
- Automatically deploying, blocking, rolling back or disabling AI systems.
- Declaring a system safe for all contexts or permanently safe.
- Certifying compliance with NCA, SDAIA, SAMA, PDPL or other frameworks.
- Treating SHA-256 as identity, non-repudiation or proof of truth.
- Treating an emergency classification as permission to bypass mandatory safety controls.
