# Mubayyin Action Mandate Assurance
## ضمان سلامة تفويض الأفعال

**Status:** proposed engineering capability, implemented as a deterministic assessment library; not yet a live execution-control gateway.

### Product boundary
Mubayyin remains an independent AI release-assurance and evidence platform. This capability extends assessment coverage to consequential actions. It does not turn Mubayyin into an agent framework, payment processor, identity provider, or action-execution service.

The library evaluates one proposed action against one versioned mandate snapshot. It checks the mandate issuance and expiry window, revocation, actor, principal, action, resource, currency, amount, delegation constraints, duplicate-execution signal and context completeness. It returns a decision and integrity fingerprints. It does not execute, block, retry, reverse, or compensate for an action. A separately controlled customer execution system must enforce the result.

### Mubayyin terminology

| English term | Arabic term | Meaning |
|---|---|---|
| Action Mandate | تفويض الفعل | Versioned statement of authority for a defined action |
| Mandate Record | سجل التفويض | Stored mandate and policy version |
| Mandate Snapshot | لقطة التفويض | Exact mandate state used for one assessment |
| Principal | صاحب الصلاحية | Person or organisation on whose behalf the action is proposed |
| Acting Agent | الوكيل المنفّذ | Agent or service proposing the action |
| Permitted Delegate | الوكيل المفوّض | Actor explicitly included in the mandate boundary |
| Action Proposal | مقترح الفعل | Exact action submitted for assessment |
| Action Conformance | مطابقة الفعل | Comparison of the proposal with mandate limits |
| Mandate Validity | سريان التفويض | Whether the mandate is active and unexpired at assessment time |
| Delegation Path | تسلسل التفويض | Declared chain through which authority was delegated |
| Action Assessment | تقييم الفعل | Deterministic assessment of one proposal against one mandate |
| Assessment Evidence | أدلة التقييم | Version references, decision reasons and cryptographic fingerprints |
| Human Confirmation | تأكيد بشري | Human confirmation required before a customer execution system proceeds |

### Decision vocabulary
| API value | English display | Arabic display |
|---|---|---|
| permitted | Permitted within mandate | مسموح ضمن التفويض |
| review_required | Human review required | يتطلب مراجعة بشرية |
| rejected | Rejected by mandate controls | مرفوض وفق ضوابط التفويض |

These decisions are separate from Mubayyin release outcomes (SAFE_TO_SERVE, CONDITIONAL_SERVE, HOLD_FOR_REPAIR). A release outcome never grants authority for an individual action.

### Assessment sequence
1. Validate timestamps and numeric values.
2. Read the exact mandate version and policy version supplied to the assessment.
3. Check mandate revocation and expiry at the evaluation instant.
4. Compare principal, acting agent, action type, resource, currency and amount.
5. Validate declared delegation against the mandate's permitted delegates.
6. Check duplicate-execution signal supplied by the customer integration.
7. Return a deterministic decision with reason codes and SHA-256 fingerprints.

### Initial reason codes
MANDATE_REVOKED, MANDATE_EXPIRED, PRINCIPAL_MISMATCH, ACTOR_NOT_AUTHORISED, ACTION_OUTSIDE_MANDATE, RESOURCE_MISMATCH, CURRENCY_MISMATCH, AMOUNT_EXCEEDS_LIMIT, POSSIBLE_DUPLICATE_EXECUTION, DELEGATION_PATH_INCONSISTENT, DELEGATION_OUTSIDE_MANDATE, ASSESSMENT_CONTEXT_INCOMPLETE, HUMAN_CONFIRMATION_REQUIRED, MANDATE_CONDITIONS_SATISFIED.

An explicit violation results in rejected. Missing context or a policy requiring human confirmation results in review_required. Only a complete matching assessment returns permitted.

### Engineering limits and safeguards
- The library is deterministic and has no model calls.
- It assesses a supplied mandate snapshot; it does not independently query a bank's live authorisation system. Integrations must obtain a fresh authoritative snapshot immediately before the customer-controlled execution boundary.
- A duplicate-execution flag is an input from the integration. This library does not provide distributed idempotency or guarantee exactly-once execution.
- SHA-256 fingerprints detect changes to assessed content; they do not authenticate the issuer or prove that the mandate was genuine.
- A customer execution boundary must fail closed on unavailable or uncertain assessment results.
- No live payment, account, customer or production data is needed for the initial benchmark. Use synthetic identifiers and values.
- Do not describe this capability as regulatory approval, certification or a guarantee of safety.

### Test benchmark
The initial suite covers valid mandates, revocation, expiry, actor mismatch, changed resources, amount and currency limits, delegation, duplicate-execution signals, incomplete context, human confirmation, timezone validation and evidence reproducibility.

### Invited-tenant API (feature branch)

- POST /tenant/action-mandates — create an immutable tenant-scoped mandate snapshot.
- POST /tenant/action-mandates/{mandate_id}/revoke — append a revocation event.
- POST /tenant/action-assessments — assess a proposal using server evaluation time and store immutable evidence.
- GET /tenant/action-assessments/{assessment_id} — retrieve the assessment within the owning tenant.

All endpoints require the invited tenant bearer key. The assessment ID is generated by the engine and returned by the API. The current API stores mandate and assessment payloads in the existing tenant-scoped PostgreSQL evidence table. This feature branch still requires automated API tests and a live PostgreSQL restart/readback and two-tenant isolation test before any production claim.

### Customer-runner SDK example

```python
from sdk.python.mubayyin_client import MubayyinClient

client = MubayyinClient(
    "https://mubayyin-web-production.up.railway.app",
    api_key="LOAD_FROM_YOUR_SECRET_MANAGER",
)

mandate = client.create_action_mandate(
    mandate_id="refund-case-88-v1",
    mandate_version="1",
    policy_version="bank-policy-2026-10",
    principal_id="synthetic-customer-001",
    authorised_actor_id="synthetic-agent-001",
    permitted_actions=["prepare_refund"],
    resource_id="synthetic-case-88",
    currency="AED",
    maximum_amount="250.00",
    issued_at="2026-10-30T10:00:00+00:00",
    expires_at="2026-10-30T12:00:00+00:00",
)

assessment = client.assess_action(
    mandate_id=mandate["mandate_id"],
    request_id="synthetic-request-001",
    principal_id="synthetic-customer-001",
    actor_id="synthetic-agent-001",
    action_type="prepare_refund",
    resource_id="synthetic-case-88",
    currency="AED",
    amount="125.00",
    proposed_at="2026-10-30T10:05:00+00:00",
)
print(assessment["decision"], assessment["reason_codes"])
```

The sample is illustrative and must use timestamps appropriate to the test run. The API uses its own server clock for the assessment instant. Never use this demo with real customer or payment data.

### Remaining verification gates
1. Run the full GitHub Actions suite and fix any failures.
2. Verify live PostgreSQL create → restart → retrieve for mandates, revocations and assessments.
3. Verify two-tenant isolation, duplicate IDs, concurrency and immutable-record conflicts.
4. Add customer-specific policy mappings and expanded Arabic/English scenario fixtures.
5. Only then evaluate a customer-controlled runtime integration. Do not make the assessment service itself execute consequential actions.
