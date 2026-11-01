# Mubayyin Phased R&D Architecture

**Status:** Proposed architecture and research work programme  
**Programme horizon:** 12 months, subject to QSTP pathway confirmation  
**Product:** Mubayyin Release Assurance  
**Owner:** Mubayyin AI Technology  
**Founder:** Raheem Larry

> This document defines the intended research architecture. It does not assert that the proposed engines, datasets, benchmarks, staffing or performance targets have already been implemented or validated.

## 1. Mission and product boundary

Mubayyin is developing independent AI release-assurance infrastructure for financial institutions and other organisations deploying consequential AI. It connects:

**Test → Prove → Decide → Release → Watch → Retest**

The system evaluates evidence and records assurance decisions. It does not provide regulatory certification, guarantee AI safety, replace institutional risk owners, or autonomously approve high-risk releases.

The existing MVP remains the foundation. Existing tenant isolation, system-version snapshots, Release Records, risk assessments and customer-controlled evaluation must be preserved. New research capabilities are introduced behind explicit interfaces and feature gates; they must not silently change existing release semantics.

## 2. Target architecture

```text
Customer-controlled evaluation environment
        |
        v
Evidence Intake & Provenance Boundary
        |
        v
Mubayyin Assurance Core
  |          |           |            |
  v          v           v            v
Linguistic  Behaviour   Decision    Evidence
Assurance   Intelligence Assurance  Integrity
  |          |           |            |
  +----------+-----------+------------+
                     |
                     v
           Assessment Orchestrator
                     |
           Policy & Human Review Gate
                     |
                     v
          Immutable Release Record
                     |
                     v
       Continuous Assurance / Retest
```

### Shared platform services

1. **Tenant and identity boundary:** tenant-scoped access, least privilege, key lifecycle and audit events.
2. **System Version Registry:** immutable version identity, configuration fingerprint and predecessor references.
3. **Scenario and Benchmark Registry:** versioned test definitions, dataset provenance, labels, language and permitted use.
4. **Assessment Orchestrator:** runs deterministic checks and approved evaluators against a pinned system snapshot.
5. **Evidence Store:** stores canonical inputs, outputs, findings, provenance and cryptographic attestations subject to retention policy.
6. **Policy Engine:** evaluates mandatory controls, severity, uncertainty and required human approvals.
7. **Release Record Ledger:** records the exact evidence, policy version, system snapshot and approval state supporting each decision.
8. **Continuous Assurance Scheduler:** accepts customer-authorised retest events and creates new assessments without mutating historic records.

## 3. Research work packages

### WP1 — Arabic-English Financial AI Assurance

**Objective:** Develop reproducible evaluation methods for Arabic and English financial-service AI, including selected Gulf dialect and code-switching cases.

Work:
- Build a licensed, provenance-tracked financial scenario corpus.
- Define language, dialect, intent, financial concept, severity and escalation labels.
- Cover account information, loan enquiries, payment instructions, complaints, fees, dates, currencies and human handoff.
- Develop deterministic checks for numerical and policy-critical content.
- Evaluate semantic methods against expert-labelled reference cases.
- Report results by language, dialect, scenario and risk class.

Outputs:
- Versioned bilingual benchmark and annotation handbook.
- Bilingual evaluation adapter behind a stable evaluator interface.
- Error taxonomy and benchmark report.

Validation:
- Independent qualified Arabic and financial-domain reviewers.
- Held-out test set and reviewer-agreement measurement.
- Precision, recall, F1, false-positive and false-negative rates by category.
- Repeated-run and cross-model comparisons.

Boundary: no claim of universal Arabic dialect coverage or reliable semantic understanding until measured.

### WP2 — Verifiable Evidence Integrity

**Objective:** Bind evidence to the exact system version, assessment, policy and authorised issuer.

Work:
- Canonicalise evidence payloads and define schema versions.
- Create signed evidence manifests with signer identity, key identifier and timestamp provenance.
- Introduce asymmetric signing and key rotation/revocation procedures.
- Bind snapshots, assessments, approvals and Release Records.
- Detect mutation, omission, duplication, broken lineage and invalid signatures.
- Build portable evidence bundles and an independent verifier.

Outputs:
- Signed evidence-manifest specification.
- Key-management and trust-boundary design.
- Offline verification utility and adversarial test suite.

Validation:
- Mutation tests for every signed field.
- Invalid, expired, revoked and unknown-key tests.
- Replay, substitution and cross-tenant tests.
- Restore and key-rotation exercises.

Boundary: a hash alone is an integrity fingerprint, not issuer authentication. A valid signature authenticates a signing key, not the truth of the underlying assertion.

### WP3 — Behaviour Change Intelligence

**Objective:** Identify material behavioural regressions following model, prompt, retrieval, tool, policy or configuration changes.

Work:
- Pin benchmark runs to exact system snapshots.
- Establish baseline distributions for scenario outcomes.
- Compare new results using deterministic and statistical methods.
- Define severity-weighted regression thresholds.
- Separate expected model variation from policy-critical regressions.
- Link each finding to changed inputs and affected scenarios.

Outputs:
- Baseline comparison service.
- Regression taxonomy and change-impact report.
- Threshold calibration and benchmark results.

Validation:
- Controlled change experiments.
- Labelled positive and negative regression sets.
- Recall, precision, false-alert rate and detection latency.
- Cross-model and repeated-run robustness tests.

Boundary: no claim that all model drift or all harmful behaviour can be detected.

### WP4 — Financial AI Decision Assurance

**Objective:** Produce explainable, policy-bound release assessments with explicit uncertainty and human accountability.

Work:
- Define a configurable financial AI risk taxonomy.
- Map scenarios to approved institutional policies.
- Separate mandatory deterministic controls from model-assisted interpretation.
- Define severity, evidence sufficiency and uncertainty handling.
- Require human approval for designated high-risk decisions.
- Preserve policy version, reviewer identity, rationale and decision timestamp.

Outputs:
- Versioned policy schema and reference policy packs.
- Decision trace and approval record.
- Cross-reviewer consistency report.

Validation:
- Expert-reviewed benchmark decisions.
- Policy mutation and boundary tests.
- Inter-reviewer agreement and decision consistency.
- Fail-closed tests for missing evidence and unresolved critical findings.

Boundary: policy packs are configurable technical controls, not legal advice or regulatory approval.

### WP5 — Continuous Assurance

**Objective:** Keep assurance evidence current as customer-controlled AI systems change.

Work:
- Define approved release baselines and material-change events.
- Accept signed, customer-authorised evaluation results.
- Trigger reassessment based on policy and change impact.
- Compare new evidence with the previous approved release.
- Preserve historical records and approval lineage.
- Produce retest, review or hold recommendations.

Outputs:
- Continuous-assurance event contract.
- Retest orchestration workflow.
- Version-to-version assurance history.

Validation:
- Simulated model, prompt, retrieval and policy changes.
- Duplicate event and replay handling.
- Out-of-order event and unavailable-provider tests.
- Tenant isolation and audit completeness tests.

Boundary: customer retains model execution and production-data control. No unrestricted production access is required.

## 4. Phased delivery and stage gates

| Period | Work | Gate and exit evidence |
|---|---|---|
| Months 1–2 | Baseline audit, requirements, risk taxonomy, dataset governance, threat model | G1: approved research specifications and baseline |
| Months 3–4 | WP1–WP4 prototypes, evidence manifest and benchmark v0 | G2: demonstrable prototypes and repeatable tests |
| Months 5–6 | Integrate evaluation, evidence, regression and policy services | G3: end-to-end assessment with version-bound evidence |
| Months 7–9 | Adversarial testing, independent review, recovery and security validation | G4: benchmark reports, defect register and independent findings |
| Months 10–12 | Continuous assurance integration, controlled demonstrations and pilot-readiness | G5: pilot package, operational documentation and commercial roadmap |

A work package does not pass a gate because code exists. It must meet its acceptance criteria and publish a reproducible validation report. Failed gates trigger remediation and scope adjustment, not unsupported claims.

## 5. Proposed research metrics

Targets below are hypotheses for planning and must be recalibrated after baseline measurement. They are not current product performance claims.

| Metric | Initial target |
|---|---:|
| Expert-labelled bilingual scenarios | 1,000–1,500 |
| Reviewer agreement | Cohen's kappa or suitable equivalent >= 0.75 |
| Precision on agreed critical deterministic checks | >= 90% |
| Recall on held-out critical regression benchmark | >= 90% |
| Defined evidence mutation cases detected | 100% |
| Designed cross-tenant negative cases rejected | 100% |
| Deterministic output repeatability under pinned inputs | >= 99% |
| Valid benchmark bundles verified / altered bundles rejected | 100% |
| Benchmark decisions linked to policy and evidence | 100% |

Report confidence intervals, class balance, test-set provenance and limitations. Do not optimise a single aggregate score at the expense of critical false negatives.

## 6. Proposed team

- Founder / CEO — product direction, programme leadership, partnerships and commercial strategy.
- Technical Lead / CTO — architecture, engineering quality, security and delivery.
- AI/ML Research Engineer — bilingual evaluation and behaviour analysis.
- Backend / Security Engineer — evidence integrity, APIs, cryptography and reliability.
- Arabic Financial Domain Researcher — corpus design, annotation and specialist review.
- Financial Services Assurance Advisor — risk policy and institutional review.
- QA / Validation Engineer — automated, adversarial and benchmark testing.

Initial hiring assumption: three core full-time technical roles, with specialist domain and validation support initially part-time or contracted. Hiring is gated by confirmed resources and programme acceptance.

## 7. Budget assumptions

Indicative 12-month planning baseline: **QAR 1,090,000**. This is a resource estimate, not a QSTP funding request or confirmed award.

| Category | QAR |
|---|---:|
| Technical Lead / CTO | 192,000 |
| AI/ML Research Engineer | 168,000 |
| Backend / Security Engineer | 156,000 |
| Arabic financial research and review | 84,000 |
| Specialist assurance advice | 40,000 |
| Dataset development and annotation | 90,000 |
| Cloud, compute and software | 65,000 |
| Independent security and technical testing | 70,000 |
| Legal, IP and company setup | 50,000 |
| Travel and institutional engagement | 35,000 |
| Contingency | 140,000 |
| **Total** | **1,090,000** |

All figures require local quotations and validation. Founder compensation, tax, flights, visa, accommodation and personal living costs are excluded pending written QSTP clarification. Subsidy eligibility and reimbursement timing must not be assumed.

## 8. IP, data and research governance

- Maintain an inventory of pre-existing Mubayyin IP and new programme-generated IP.
- Record code provenance, contributor agreements, dataset licences and invention disclosures.
- Obtain written agreements before university, contractor or third-party contributions.
- Confirm ownership, licence-back, publication and background-IP terms before signing any incubation or research agreement.
- Use synthetic, public-domain or appropriately licensed data unless customer data use is expressly authorised and contractually governed.
- Apply data minimisation, retention limits, access controls and deletion procedures.
- Keep customer model execution under customer control.
- Do not publish confidential institutional data or benchmark examples that expose customer information.

## 9. Architecture integration rules

1. New research engines must use versioned interfaces and must not bypass the existing tenant boundary.
2. Every evaluation must identify the system snapshot, evaluator version, scenario-set version and policy version.
3. Research outputs must be reproducible and traceable to source evidence.
4. Model-assisted evaluators are advisory evidence sources; deterministic controls and explicit policy rules remain separately identifiable.
5. Missing, contradictory or unverifiable evidence must fail closed or require human review according to policy.
6. Historical Release Records are immutable; reassessment creates new linked records.
7. Feature flags control experimental capabilities. No research prototype becomes a production default without passing its gate.
8. No customer production data or external model credentials are required for the default research workflow.

## 10. Commercialisation objective

The initial market wedge is Arabic-English customer-facing AI in regulated financial services in Qatar and the GCC. Commercial validation will use controlled demonstrations, customer-authorised trials, pilot conversion and paid usage evidence.

The intended recurring value is assurance across the AI lifecycle: before release, at release, after release and after material changes.

The programme succeeds when it produces validated technical capabilities, an independently reviewable evidence model, credible institutional pilot readiness and a sustainable commercial path—not merely when all planned modules have been coded.
