# Mubayyin — Qatar Market, Competitive Position and Startup Qatar Evidence Dossier

**Status:** Desk-research baseline; not a completed customer-validation study  
**Version:** 0.1 · 30 October 2026  
**Launch wedge:** Qatar financial-services AI workflows, starting with Arabic/English customer service  
**Product:** Vendor-neutral AI Release Assurance

## 1. Executive position

Mubayyin should not apply as another generic AI governance dashboard or another LLM evaluation tool. The defensible product proposition is narrower:

> **Mubayyin turns a specific AI application version's test evidence, required scenario coverage, human review and configuration identity into a reproducible release decision record.**

The first customer workflow is an Arabic/English financial-services assistant. The initial buyer group is AI product/engineering leaders working with model-risk, compliance, security and quality owners. The buyer's practical question is: *What exactly did we test on this version, what failed, what did we not test, who reviewed it, and why was it allowed to proceed?*

Mubayyin is an evidence and decision workflow. It does not certify compliance, determine legal compliance, guarantee model safety or replace a bank's risk owner.

## 2. Qatar market evidence

### 2.1 National AI and cyber context

- Qatar's International Media Office describes AI as part of national transformation and identifies AI strategy pillars including education, data access, employment, business, research and ethics. It also describes Digital Agenda 2030 targets including 26,000 ICT jobs and QAR 40 billion in annual digital economic impact by 2030. These are national targets, not Mubayyin forecasts. Source: [International Media Office — Artificial Intelligence in Qatar](https://imo.gov.qa/en/priorities/artificial-intelligence).
- Qatar's National Cyber Security Agency AI Guidelines cover public and private organisations using or intending to deploy AI systems. They discuss cybersecurity of AI and trustworthiness topics including oversight, robustness, accuracy, explainability, transparency, traceability and data privacy. This creates a relevant policy context for an evidence-led assurance product; it does not mean Mubayyin is approved by NCSA or satisfies every guideline. Source: [NCSA — Guidelines for Secure Adoption and Use of Artificial Intelligence](https://ncsa.gov.qa/sites/default/files/2024-02/AI-Guide-en-V6.pdf).
- Qatar's National Cyber Security Strategy 2024–2030 highlights cyber resilience, legislation and governance, a data-driven economy, research and innovation, workforce capability and cooperation. Mubayyin's intended contribution is a commercial software capability in the AI assurance and evidence workflow—not a substitute for national cybersecurity controls. Source: [NCSA — National Cyber Security Strategy](https://www.ncsa.gov.qa/en/national-cyber-security-strategy).
- Qatar's Central Bank FinTech Strategy identifies financial infrastructure, fintech talent, innovation, financial institutions, insurers, capital-market firms, vendors, regulators, accelerators and universities as ecosystem participants. It explicitly identifies a regulatory sandbox as market infrastructure. This is a relevant route for bounded, synthetic-data testing and future partner evaluation; it is not evidence of an existing Mubayyin relationship. Source: [QCB — FinTech Sector Strategy](https://www.qcb.gov.qa/Documents/SuperVision/FENTECHStrategy_EN.pdf).
- QCB's published supervision remit includes banks, insurance companies, financial technology companies and other financial institutions, with risk-based supervision and oversight. QCB also identifies digital transformation, data governance, cybersecurity and financial technology as institutional responsibilities. These facts support selecting financial services as the first vertical; they do not imply that QCB has requested or endorsed Mubayyin. Sources: [QCB — Supervision Sector](https://www.qcb.gov.qa/en/Supervision/pages/supervision-sector.aspx) and [QCB — Technology & Digital Transformation Sector](https://www.qcb.gov.qa/en/technologyanddigitaltransformationsector/pages/technology-and-digital-transformation-sector.aspx).

### 2.2 Initial target-account universe

Use this as a prospect research list, not a claim of demand or partnership. The QCB retail-payment systems pages identify a broad set of participating financial institutions and payment providers, including:
- Qatar National Bank (QNB)
- Commercial Bank
- Qatar Islamic Bank (QIB)
- Doha Bank
- Ahli Bank
- Qatar International Islamic Bank (QIIB)
- Dukhan Bank
- AlRayan Bank
- Qatar Development Bank
- HSBC Qatar
- Standard Chartered Qatar
- Arab Bank
- BNP Paribas Qatar
- Sadad
- Ooredoo Money
- Other authorised payment service providers

Source: [QCB — Retail Payment Systems and Members](https://www.qcb.gov.qa/en/Pages/Retail-payment-systems.aspx).

**First segment:** a single bank, fintech or payment provider running a customer-service AI workflow in Arabic/English.

**Adjacent segments after the first use case works:** insurance claims/service assistants, public-service assistants, telecom support, enterprise internal assistants and higher-risk agentic workflows.

Do not attempt to sell to every sector at once. The first commercial proof should be one buyer, one AI workflow, one agreed scenario set and one release decision.

### 2.3 Buyer map

| Role | Why they care | Mubayyin value to demonstrate |
|---|---|---|
| Head of AI / digital product | Wants to ship AI without losing control of version changes | Version-specific test evidence and repeatable retesting |
| AI engineering / ML platform | Needs a test workflow that fits build and deployment practices | API, customer-controlled runner, scenario versioning |
| Model risk / risk management | Needs clear boundaries, risk coverage and human accountability | Required scenario coverage, reason codes, reviewer record |
| Compliance / conduct risk | Needs evidence that policies were tested, not just stated | Versioned disclosure, privacy and escalation scenarios |
| CISO / data protection | Needs control over sensitive test data and access | Tenant separation, local execution option, data minimisation |
| QA / assurance | Needs reproducible regression testing | Fixed scenario packs, hashes, export and offline verification |

## 3. Competitive stress test

Mubayyin is not entering an empty market. The following vendors already describe overlapping capabilities. This is why the product must be sharply positioned and technically differentiated rather than claiming that AI evaluation or AI governance is new.

| Competitor / substitute | Publicly described strengths | Mubayyin's credible distinction to test |
|---|---|---|
| Credo AI | AI inventory/registry, risk management, policy, compliance, monitoring, evidence retrieval and governance workflows | Focus on version-bound pre-release evidence and required test coverage as a release decision artifact; do not claim Credo lacks these features |
| Patronus AI | LLM evaluators, experiments, benchmark datasets, logs, traces, comparisons and production evaluation | Add a release gate that binds scenario coverage, configuration identity, reviewer decision and portable evidence into one record |
| LangSmith | Offline/online evaluations, datasets, experiment comparisons, human annotation, prompt iteration and CI evaluation | Remain vendor/framework neutral and centre the customer-owned release record and evidence verification, not trace analytics or prompt tooling |
| Arthur | Agent discovery, runtime security, governance, policy enforcement, audit logs and risk assessment | Start with pre-release, version-specific proof and bounded release decisions rather than broad agent discovery/runtime security |
| Internal spreadsheets, test scripts, tickets and GRC workflows | Familiar, cheap, already embedded in teams | Offer a repeatable, machine-verifiable workflow that reduces manual evidence assembly and makes coverage gaps explicit |

Official product references:
- [Credo AI product](https://www.credo.ai/product)
- [Patronus AI](https://www.patronus.ai/llm)
- [LangSmith evaluations](https://www.langchain.com/langsmith/evaluation)
- [Arthur](https://www.arthur.ai/)

### 3.1 What is not a moat

- A dashboard, scenario library, API, hash, AI score or PDF export alone is copyable.
- "Arabic AI governance" is not a defensible claim until the language data, review process and repeatable results exist.
- A hash proves that the exported bytes match a hash; it does not prove the underlying model response was correct or safe.
- A generic LLM judge is not a moat and cannot be the sole release authority.

### 3.2 Potential moat to earn

1. **Release Evidence Graph:** each trial is bound to exact system and scenario fingerprints; each release record references the evidence and required coverage; each retest can be compared with its predecessor.
2. **Coverage Gate:** required tests that were not run are explicit missing evidence and can force HOLD, rather than silently disappearing from an average score.
3. **Portable Evidence:** export bundles contain the record and supporting evidence and can be verified independently; authenticity is distinguished from integrity.
4. **Human Accountability:** named reviewer, decision, override and rationale are recorded; the system does not silently convert an automated score into approval.
5. **Customer-Controlled Execution:** a future runner executes against customer-approved endpoints in the customer's environment; credentials remain with the customer and only approved evidence is sent.
6. **Qatar/GCC Scenario Foundry:** curated, versioned Arabic/English financial-services and service-workflow tests, reviewed by qualified domain and language experts, with explicit dialect and coverage limits.
7. **Operational trust:** tenant isolation, durable retrieval, access logs, retention controls and security review. These must be demonstrated, not described as a moat prematurely.

The combination may become difficult to replace after it is embedded in release workflows and scenario history. It is not uncopyable by assertion.

## 4. Initial product proof

The new synthetic Qatar pack contains 12 Arabic, English and bilingual financial-services scenarios covering disclosures, privacy canaries, escalation, identity verification, unauthorised actions, fraud and refund-status claims.

It is a **synthetic engineering fixture**, not a regulator-approved policy pack, validated Qatari Arabic benchmark or customer dataset. A qualified local language/domain review is required before commercial use.

The PoC demonstration must show:
- An intentionally failing baseline.
- Exact deterministic findings and what those checks do not detect.
- A required-scenario omission forcing HOLD.
- A repaired retest with a changed evidence hash.
- A human review and a release record.
- An export bundle and offline integrity verification.
- Two-tenant isolation and persistence after an actual database restart.

## 5. Commercial model and conversion path

This is a pricing hypothesis to test, not a published price or validated willingness-to-pay result.

### Funnel
1. **Free Evaluation:** synthetic test lab, limited scenarios and trial runs, no production data.
2. **Paid Pilot:** fixed scope for one AI workflow, one policy/scenario pack, agreed test volume, reviewer workflow and evidence export.
3. **Team subscription:** recurring access for multiple systems, scenario libraries, release history, reviewers and API usage.
4. **Enterprise:** customer-controlled runner, private deployment option, identity integration, retention controls, policy packs, support and audit exports.

### Initial pricing hypotheses (QAR; test, do not claim as established)
- Free Evaluation: QAR 0, bounded synthetic use.
- Paid Pilot: QAR 12,000–25,000 for a 4–6 week, one-workflow evaluation.
- Team: QAR 3,000–7,500 per month, scoped by active systems, runs and seats.
- Enterprise: annual agreement priced after deployment, integration, security and support scope is known.

Do not submit these as validated market prices. Test actual checkout or signed pilot conversion; do not count page visits, positive comments or unpaid interviews as proof of willingness to pay.

### Revenue logic
- Pilot services produce initial revenue and workflow learning.
- Recurring Team subscriptions monetise ongoing regression and release evidence.
- Enterprise annual contracts monetise integration, private execution, retention, identity and support.
- Scenario packs can become add-on modules only after they are reviewed, versioned and repeatedly used.

## 6. Qatar operating plan

### First 12 months (proposed milestones)

| Period | Product / business milestone | Evidence to retain |
|---|---|---|
| Months 1–3 | Complete PoC and secure invited-pilot MVP; establish Qatar operating plan | Test results, code release, database restore, isolation report, demo |
| Months 4–6 | Run first controlled evaluation with an approved Qatar-based design partner; no sensitive data without contractual and security approval | Signed pilot scope, baseline/retest, reviewer record, outcome report |
| Months 7–9 | Convert pilot to paid recurring use; improve Arabic evaluation and customer-runner integration | Payment/conversion evidence, scenario review log, runner tests |
| Months 10–12 | Expand to additional financial-services workflows and one adjacent sector; recruit local technical/evaluation capacity | Renewals, usage, new jobs, local reviewer contracts, release metrics |

No partner, pilot, job, revenue or customer is claimed until it exists and can be evidenced.

### Qatar contribution

- Establish product engineering and commercial operations in Qatar subject to programme and legal advice.
- Recruit/contract local software engineering, security and Arabic evaluation talent as funding and demand justify.
- Build Arabic/English test assets with local domain experts and qualified language reviewers.
- Support financial-services and enterprise AI teams with repeatable assurance tooling.
- Collaborate with local universities, accelerators and technology providers where agreements are reached.
- Expand from Qatar into the GCC only after a repeatable Qatar pilot and support model exist.

## 7. Startup Qatar application evidence map

The official START programme description should be checked at application time for current eligibility, funding and documentation. The published programme describes the START path for technology startups with a proof of concept or MVP seeking to establish operations in Qatar and refers to concept validation, unmet need, execution/technology roadmap, market research, business/monetisation model and committed leadership.

Official programme page: [Startup Qatar — Investment Program](https://startupqatar.qa/en/investment-program).

| Assessment area | Application evidence required | Current truth / gap |
|---|---|---|
| Problem and unmet need | Customer workflow problem, cost of current manual evidence, failure examples | Desk research supports context; buyer evidence still needed |
| PoC/MVP | Live demo, private workspace, scenario pack, evidence bundle, verifier | Public demo and code foundation exist; Railway pilot validation still required |
| Technology and differentiation | Architecture, release-evidence model, required coverage gate, isolation and verification tests | Core design exists; security and live durability gates remain |
| Market research | Qatar target accounts, buyer roles, substitutes, competitor analysis, pricing hypothesis | This dossier is a desk-research baseline; not completed customer validation |
| Monetisation | Free evaluation, paid pilot, Team subscription and Enterprise route | Model defined; price points remain hypotheses |
| Execution roadmap | Gated 12-month milestones, owners, dependencies and acceptance criteria | Build contract exists; add named owners and costed milestones |
| Qatar contribution | Qatar operating plan, jobs, local R&D and local language review | Proposed contribution; not yet delivered |
| Team and leadership | Founder CV, technical leadership, domain advisors, hiring gaps and commitment | Must be supplied and evidenced by the founder |
| Financial plan | 18-month cashflow, salaries, cloud/security costs, pilot costs, runway and milestone-linked use of funds | Must be costed from actual quotes and hiring assumptions |
| Risk and governance | Data flow, privacy, security, model limitations, human accountability and non-certification boundary | Partial; security review, retention/deletion and legal documents remain |

## 8. Use-of-funds structure (percentage planning hypothesis)

Do not choose a funding ask by starting from the programme maximum. Build the budget from the actual milestone plan and local operating costs.

| Workstream | Planning allocation |
|---|---:|
| Core product, customer-controlled runner and integrations | 35% |
| Security, privacy, tenant isolation, backup and assurance | 20% |
| Arabic/bilingual scenario quality and expert review | 15% |
| Qatar pilots, market access and partner delivery | 15% |
| Qatar-based technical and evaluation talent | 10% |
| Legal, administration and operating contingency | 5% |

The final application should replace percentages with named hires, monthly cost, vendor quotes, milestones, deliverables and runway.

## 9. Application risks and how to answer them honestly

- **"How is this different from LangSmith/Patronus/Credo/Arthur?"** Show the version-bound release record, coverage gate, evidence bundle, human signoff and customer-controlled execution. Acknowledge overlap; do not claim an empty market.
- **"Does it understand Arabic?"** Show only the tested Arabic scenarios and reviewer status. The present reference engine does not prove semantic Arabic quality or dialect coverage.
- **"Is it certified or regulator-approved?"** No. It is a vendor-neutral assurance tool and does not issue certification or legal compliance determinations.
- **"Does it connect to live AI models?"** The public test lab accepts supplied synthetic outputs. A customer-controlled endpoint runner is the next integration gate; do not claim it is live until tested.
- **"Is evidence durable?"** Tenant persistence is implemented in the branch and unit-tested against SQLite fixtures; a real Railway/PostgreSQL restart-and-retrieve test remains mandatory.
- **"Are customer records secure?"** Do not use production customer data until tenant isolation, credentials, retention, security review and contractual data processing controls are approved.
- **"Who has adopted it?"** State actual customers, pilots, revenue and partnerships only when documented. Otherwise say "pre-commercial; pilot-ready work in progress."

## 10. Decision

Keep the Qatar financial-services wedge as the first proof. Build the complete product workflow before widening the sector list. The programme application should be supported by an executable demo, a secure private pilot, a reproducible evidence bundle, a market/competitor dossier, a costed Qatar plan and founder/team evidence—not by website polish alone.
