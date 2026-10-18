# Mubayyin — Release Assurance Engine (v0.1 scaffold)

This is the smallest real version of the loop in the strategy doc:

```
AISystem  →  ScenarioCase[]  →  TrialResult[]  →  ReleaseRecord
```

## What's actually verified (run this first)

```bash
python3 demo.py          # end-to-end run, prints a real Release Record
python3 -m unittest tests.test_engine -v   # 13 tests, all passing
```

Both use **zero external dependencies** — pure Python 3 standard library —
so they run anywhere with no setup. This is the part of the project I could
fully test and prove works in this environment.

What the demo proves:
- A privacy leak and an unauthorized transfer are caught by **deterministic
  checks**, not by asking a model to grade itself.
- A human review record attaches to a finding rather than silently
  overwriting the automated one.
- Any release with an unresolved critical failure becomes `hold_for_repair`,
  and any non-`safe_to_serve` record without a named approver is marked
  provisional.
- Every record carries a `config_hash` (exactly what was tested) and an
  `evidence_hash` (what the result was), so it's reproducible.

## What needs you to run it locally (not testable in the build sandbox — no network there)

```bash
pip install -r requirements.txt
uvicorn app.api:app --reload
# open http://127.0.0.1:8000/docs
```

This wraps the same, already-tested `app/models` and `app/services` code in
a real HTTP API (`/systems`, `/scenarios`, `/trials`, `/trials/{id}/review`,
`/releases`). It uses standard, well-established FastAPI patterns, but I
could not execute it myself in this sandbox because it has no network
access to `pip install` — so treat it as "should work, verify on your
machine," not "proven," until you've run it.

## What is deliberately NOT built yet (and why)

Per the strategy doc's validation gates — none of this should be built
before you have paying pilots and a changed production decision:

- PostgreSQL-backed evidence storage is implemented in the API when DATABASE_URL is configured. It persists systems, scenarios, trials, reviews, and release records and restores them at startup. A live database-backed restart/restore test is still required before claiming end-to-end durability has been verified.
- Real LLM judge (currently a transparent lexical-overlap stand-in in
  `app/services/evaluator.py::reference_judge` — replace with an actual
  model call behind the same `JudgeFn` signature, and add a second,
  independent judge before trusting disagreement checks)
- Authentication and tenant isolation, CI/CD webhooks, drift watch, SDKs
- Any of the "10 organizations use this scenario library" scale — this
  scaffold ships with 10 illustrative scenarios, not a production library

## Honest next step

Point this at one real (or realistic mocked) customer AI endpoint, load
scenarios drawn from that customer's actual policies and one real
production failure, and see if the Release Record it produces would
actually change someone's release decision. That's Gate 4 from the
strategy doc — everything else waits for it.
