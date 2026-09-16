# Phase boundaries — read before adding anything to this repo

This file exists because the strategy discussions that produced this
architecture kept generating good ideas faster than they generated paying
customers. That pattern is common enough with AI-assisted architecture
work that it's worth guarding against explicitly, in the repo itself, not
just in a strategy doc someone might not open.

## What's actually in this repo (v0.1)

- `app/models/core.py` — AISystem, ScenarioCase, TrialResult, ReleaseRecord.
- `app/services/evaluator.py` — deterministic checks + a stand-in judge.
  Severity is decided by rule-based logic, **never by an LLM directly**.
- `app/services/policy_compiler.py` — customer policy → structured
  requirement (PIR) → executable deterministic check. Not an LLM prompt.
- `app/services/release_gate.py` — turns results into a Release Record with
  a status (`safe_to_serve` / `conditional_serve` / `hold_for_repair`) and
  machine-readable reason codes.
- `app/api.py` — a thin FastAPI wrapper over the above (in-memory storage).

All of it is tested (`tests/test_engine.py`) and runs with zero external
dependencies except the optional FastAPI layer.

## What is explicitly deferred, and the gate that unlocks it

Later architecture proposals for this project introduced two additional
layers: an **Intelligent Control Plane** (change-impact analysis, risk
classification, runtime enforcement modes) and **Terrain Intelligence**
(external signal ingestion, competitor capability watch, market pattern
detection). Both are reasonable long-term ideas. Neither belongs in this
repo yet.

| Deferred capability | Don't build until | Why |
|---|---|---|
| Intelligent Control Plane (change-impact engine, risk classifier, runtime enforcement modes ALLOW/BLOCK/RESTRICT) | Gate 4 (a pilot has changed a real release decision) *and* Gate 7 (≥70% of delivery is automated) | There's nothing to "control" yet — no production system depends on a release decision this product made. Building enforcement infrastructure before that exists is building for a customer who doesn't exist yet. |
| Terrain Intelligence (public signal ingestion, competitor watch, market pattern clustering) | Never before actual legal review, and not before Phase 5 even then | This is the one that needs a lawyer before it needs a developer. Scraping/monitoring public sources at scale raises real ToS and IP questions that a strategy doc can't resolve. It also adds nothing to what a bank needs to approve a pilot. |
| CI/CD deployment blocking (Deployment Relay actually stopping a real deploy) | One real customer's CI/CD, with their explicit sign-off | Blocking someone's deployment pipeline is a production-trust responsibility, not a demo feature. |
| Multi-tenant Postgres, SSO/SCIM, customer-controlled execution modes | First paying pilot | In-memory storage is fine for a demo and a first pilot walkthrough. It is not fine for a second customer's data touching the same process. |

If you (or an AI coding agent working on this repo) are about to add code
for anything in that table, stop and check: has the corresponding gate in
the strategy doc actually been hit, with evidence, not just "it seems like
the natural next step"? If not, it doesn't belong here yet.

## Terminology map (so future sessions don't reinvent names)

The project has been described across multiple documents with different
layer names for the same concepts. Canonical names for this repo:

- **Release Record** — the root object (called MRR, Evidence Dossier root,
  and "release record" interchangeably elsewhere — pick this one).
- **Configuration fingerprint** — `AISystem.config_hash()`.
- **Policy-to-Test Compiler** — `app/services/policy_compiler.py`.
- **Trust Trial** — one `run_trial()` call, producing a `TrialResult`.
- **Reason codes** — `ReasonCode` enum in `release_gate.py`.

Don't introduce parallel objects with different names for these — extend
the existing ones.
