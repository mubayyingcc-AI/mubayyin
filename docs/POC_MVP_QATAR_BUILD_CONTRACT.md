# Mubayyin — Qatar PoC and MVP Build Contract

**Status:** Approved build direction; implementation is in progress  
**Product category:** Vendor-neutral AI release assurance  
**Launch market:** Qatar first; GCC expansion after local proof  
**Primary wedge:** Arabic/English customer-service AI in regulated financial services  
**Core loop:** Test → Prove → Decide → Release → Watch → Retest

## 1. Product thesis

Mubayyin is an assurance layer that helps an organisation determine whether a specific version of an AI application has been tested against its own stated requirements, what failed, what remains untested, who reviewed the evidence, and what release decision was recorded.

It is not an AI model, chatbot builder, general-purpose agent framework, regulator, certification body, or replacement for a customer's risk owner. Mubayyin does not declare an AI system universally safe. It creates a reproducible, bounded evidence trail for a human-owned release decision.

**Customer pain:** AI teams can demonstrate model quality, but release approval often relies on fragmented test runs, spreadsheets, tickets, prompt snapshots and undocumented human judgement. After a prompt, model, retrieval source, tool or policy changes, teams need to know what changed, what was retested, what coverage is missing and whether the prior approval still applies.

**Mubayyin outcome:** a version-bound Release Record with test evidence, configuration fingerprints, required scenario coverage, deterministic findings, reviewer decisions, reason codes and an exportable integrity-checked evidence bundle.

## 2. Why Qatar, why now

Qatar is the first operating and market-validation base, not a decorative geographic label. The launch plan is to:
- Establish the company/product development and partner-engagement pathway in Qatar, subject to programme and incorporation requirements.
- Build the first demonstrator around Arabic/English financial-service customer-support workflows, with synthetic data and explicit policy requirements.
- Seek controlled evaluation opportunities with Qatar-based financial institutions, fintechs, insurers, public-sector digital teams, universities and ecosystem organisations. No relationship is claimed until formally agreed.
- Develop Arabic and bilingual evaluation assets with qualified local reviewers; report dialect coverage honestly rather than claiming broad Arabic competence.
- Build technical capability and jobs in Qatar, then use validated Qatar evidence as the basis for GCC expansion.

The START category of Startup Qatar is the relevant programme to assess because its official description targets startups with a PoC or MVP seeking to establish operations in Qatar. Published criteria include a validated concept addressing an unmet need, a clear execution plan and technology roadmap, market research, a robust business and monetisation model, and a committed leadership team. Funding is milestone-tranched and subject to programme assessment; no acceptance, eligibility or award is assumed.

## 3. Product boundary: two modes, one evidence model

### A. Public demonstration sandbox
- Free, synthetic-data-only, session-scoped.
- No customer secrets, production credentials or confidential inputs.
- In-memory test records expire with the sandbox session.
- Clearly labels reference-evaluator limitations and the absence of certification.
- Demonstrates the complete test-to-decision flow without making public demo data part of a customer tenant.

### B. Invited organisation pilot workspace
- Tenant-authenticated API and private browser workspace.
- PostgreSQL-backed tenant records, with tenant ID included in evidence queries.
- Dedicated tenant API keys; administrator-only provisioning, rotation and revocation.
- Human review before immutable Release Record creation.
- Versioned systems and scenarios; stale evidence rejected.
- Required scenario coverage enforced; missing required scenarios result in HOLD.
- Exportable JSON evidence bundles and offline integrity verification.
- No production customer data until live restore, access-control, privacy and security gates pass.

The public sandbox and invited pilot are separate trust boundaries. Do not silently move public demo records into tenant storage.

## 4. Canonical product objects

- **AI System:** identity of the application version under test.
- **Configuration Fingerprint:** hash of model/provider version, prompt, retrieval, policy and tool versions.
- **Scenario Case:** versioned user input, expected behaviour, forbidden behaviour, risk level, language/dialect and required disclosure/escalation conditions.
- **Trust Trial:** one execution of a scenario against a specific system configuration.
- **Finding:** deterministic rule result or explicitly labelled evaluator observation.
- **Human Review:** reviewer identity/label, agreement, override and rationale.
- **Release Record:** immutable decision artifact bound to exact configuration and evidence.
- **Reason Code:** machine-readable explanation of why a release is safe-to-serve, conditional-serve or hold-for-repair.
- **Evidence Bundle:** portable record, referenced scenarios, trials and integrity metadata.
- **Coverage Gap:** a required scenario that was not executed or could not be evaluated.

No parallel naming system or duplicate score engine should be introduced.

## 5. PoC acceptance contract

The PoC is one complete, repeatable demonstration:

**Use case:** a synthetic Arabic/English financial-services customer-support assistant that must disclose approved product terms, avoid unsupported guarantees, protect customer information, and escalate when a request exceeds its authority.

The demonstrator must show:
1. Register a versioned AI system.
2. Load a small, clearly labelled synthetic policy scenario pack.
3. Run at least one passing and several deliberately failing test cases.
4. Show exact deterministic checks and their limits.
5. Record a human review.
6. Attempt release with a missing required scenario and demonstrate HOLD.
7. Complete the required coverage, rerun after a configuration change, and create a new Release Record.
8. Compare records and explain the changed evidence; never equate a changed hash with safer behaviour.
9. Export the evidence bundle and verify it offline.
10. Demonstrate that tampering changes verification outcome.
11. Demonstrate that one sandbox session cannot read another session's records.
12. Demonstrate that one tenant cannot read another tenant's records.

**PoC proof artifacts:** live demo URL, synthetic scenario pack, test run output, sample Release Record, exported JSON bundle, offline verification output, test report and a short screen-recorded walkthrough.

## 6. MVP acceptance contract

The MVP is ready for a controlled design-partner pilot only when all of the following are true:

### Product workflow
- Invited organisation can connect to its own workspace.
- Register multiple versioned AI systems and scenario sets.
- Run repeatable tests and see findings, evidence, coverage and evaluator limitations.
- Human review is recorded before release.
- Release records are immutable and stale configuration/scenario evidence is rejected.
- Required coverage is enforced.
- Records can be retrieved after application restart and exported/verified offline.
- English and Arabic interface paths work; Arabic evaluation claims are limited to tested language/dialect coverage.

### Security and privacy
- Tenant isolation is tested against two independent tenants.
- Admin and tenant credentials are separate, stored as hashes where applicable, rotated/revoked and never exposed in browser source or logs.
- Sensitive routes return no-store/private cache headers.
- Request size, input length, rate and abuse limits are enforced.
- No secret or credential is written to evidence bundles.
- Customer can use synthetic data or redact outputs; data retention/deletion and processing terms are documented.
- A real PostgreSQL restart → retrieve test passes on Railway.
- Security review covers authentication, authorization, tenant boundaries, API abuse, backup/restore, logging and dependency vulnerabilities.

### Evaluation quality
- Deterministic checks have explicit pass/fail/unevaluated states.
- High-risk privacy scenarios fail closed when no privacy check is configured.
- Exact phrase matching is not represented as semantic understanding.
- Add adversarial paraphrase, negation, code-switching, Arabic-script and false-positive regression cases.
- Human review can override a finding with traceable rationale; it cannot rewrite a record after release.
- Any LLM judge is optional, independently identified, versioned and never allowed to overrule deterministic critical checks or human approval. No single LLM judge determines release status.

### Integration
- First integration is a customer-controlled runner/adapter for a bounded test endpoint. Customer credentials stay on the customer's side; Mubayyin does not require a customer to paste production API keys into its hosted workspace.
- The runner submits only the minimum approved test material/evidence. Redaction and retention choices are explicit.
- API documentation includes authentication, schemas, error codes, rate limits and a reproducible quick-start.
- CI/CD integration is advisory initially; do not block customer deployments until a customer explicitly authorises it.

### Commercial readiness
- One clearly defined buyer and use case.
- Transparent pilot scope, pricing hypothesis, onboarding and support model.
- Free evaluation → paid pilot/conversion path; usage is a signal, not proof of willingness to pay.
- At least one controlled design-partner evaluation and documented before/after release-decision case study before claiming market validation.
- No invented customer names, partnerships, traction, revenue, certifications or Qatar endorsements.

## 7. Build sequence and gates

### Gate 0 — Baseline and truth audit
- Preserve Qatar-first production homepage and existing public test lab.
- Confirm the active Railway service, Postgres connection, `/health` and `/ready`.
- Inventory the code, environment variables and deployed commit.
- Separate public sandbox from invited-pilot APIs.
- Keep the earlier draft PR's homepage changes out of the integration.

### Gate 1 — Merge the controlled-pilot foundation
- Integrate tenant API, workspace, tenant-key lifecycle, evidence bundle and offline verifier.
- Preserve the current Qatar-first homepage.
- Run all GitHub Actions tests and inspect changed files.
- Do not provision a tenant until admin secret is configured securely.

### Gate 2 — Live persistence and isolation proof
- Configure dedicated admin credential in Railway secret variables.
- Verify PostgreSQL schema creation and `/ready`.
- Provision two synthetic test tenants.
- Create system → scenario → trial → review → release in tenant A.
- Restart/redeploy application and retrieve the record.
- Verify tenant B cannot read tenant A's records.
- Rotate/revoke keys and verify old credentials fail.
- Export and verify a bundle; tamper with a copy and verify rejection.
- Remove test tenants only through a reviewed, documented data-retention action; do not silently delete evidence.

### Gate 3 — Evaluation-quality upgrade
- Investigate the recorded privacy false-negative case.
- Add explicit configurable sensitive-data/canary checks and test suites for common identifiers without claiming complete PII detection.
- Build a curated Qatar/GCC financial-services bilingual scenario pack with source/provenance, owner, version and review status.
- Measure false positives/negatives on a documented synthetic regression set.
- Keep Arabic dialect and semantic coverage limits visible.

### Gate 4 — Customer-controlled integration
- Build a local runner/SDK that can call a customer-approved test endpoint from the customer's environment.
- Keep provider credentials local; submit only approved/redacted evidence.
- Add signed runner manifests, versioned test manifests and reproducible run IDs.
- Start with a read-only/advisory integration; no automatic deployment blocking.

### Gate 5 — Controlled pilot and application evidence
- Complete one documented pilot with synthetic or formally approved data.
- Record a baseline and a post-fix retest.
- Demonstrate a real release decision changed because of a specific finding or coverage gap.
- Build a Startup Qatar evidence dossier with architecture, demo, roadmap, Qatar execution plan, market research, monetisation, budget/milestones and founder/team evidence.

## 8. Startup Qatar application evidence map

| Programme assessment area | Evidence Mubayyin must provide |
|---|---|
| Validated concept / unmet need | Documented workflow pain, failure examples, customer problem evidence and the release-decision case study |
| Working PoC/MVP | Public demo, private workspace, test suite, repeatable run and downloadable evidence bundle |
| Technical innovation | Configuration-bound evidence, required-coverage gates, immutable Release Records, tenant isolation and verifiable exports |
| Technology roadmap | This build contract with acceptance gates, owners, dependencies and milestones |
| Market research | Qatar target-segment map, competitor/substitute analysis, buyer/user map and pricing hypotheses |
| Business model | SaaS tiers, evaluation-to-paid-pilot path, enterprise deployment/support and realistic unit economics |
| Qatar economic contribution | Qatar operating plan, planned local technical roles, local reviewer/research collaboration and sector deployment plan |
| Leadership | Founder roles, relevant experience, execution commitment and any gaps to fill |
| Use of funds | Milestone-linked engineering, security, Arabic evaluation, Qatar incorporation/operations, pilots and market access budget |
| Risk management | Privacy/security limitations, non-certification boundary, data-handling policy, human accountability and evaluation limitations |

## 9. Initial commercial model hypothesis

Do not present these as validated prices. Test willingness to convert through product use:
- **Free Evaluation:** synthetic public lab, limited runs, public evidence preview.
- **Pilot:** bounded number of systems/scenarios, private workspace, evidence export, agreed support and review cadence.
- **Team:** recurring per-system or usage-tier subscription with scenario packs and release history.
- **Enterprise:** private deployment/customer-controlled runner, policy integration, governance workflows and support.

Pricing must be based on delivery cost, buyer value and observed conversion, not a fabricated TAM or unsupported willingness-to-pay claim.

## 10. Non-goals / forbidden shortcuts

- No generic AI governance dashboard that adds no decision evidence.
- No fabricated benchmarks, certifications, customer logos, pilot results or Qatar partnerships.
- No LLM-generated novelty score or unvalidated autonomous safety score.
- No one-judge pass/fail decision.
- No automatic CI/CD blocking in the first MVP.
- No public ingestion/scraping intelligence layer.
- No storing customer secrets or model-provider credentials in Mubayyin.
- No claim that a hash proves the underlying AI output was safe or truthful.
- No claim that a successful CI run proves live production restore or security.
- No broad Arabic quality claims without reviewed dialect-specific evaluation.

## 11. Definition of done for programme-ready MVP

Mubayyin is ready to present as a functioning MVP when a reviewer can:
- Open the Qatar-first site and public demo.
- Watch the synthetic financial-services scenario run end to end.
- Connect to an invited pilot tenant.
- Inspect tenant-scoped evidence and reviewer actions.
- See missing coverage force a HOLD.
- See a changed system configuration invalidate stale evidence.
- Retrieve a record after a real Railway restart.
- Verify an exported bundle offline and detect tampering.
- Read an honest security/evaluation limitations report.
- Review a credible Qatar launch plan, buyer, monetisation model, budget and milestones.

Passing this contract improves application readiness; it does not guarantee programme acceptance or investment.
