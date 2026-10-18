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

## Run locally for a manual integration check

```bash
pip install -r requirements.txt
uvicorn app.api:app --reload
# open http://127.0.0.1:8000/docs
```

This wraps the tested `app/models` and `app/services` code in a FastAPI API (`/systems`, `/scenarios`, `/trials`, `/trials/{id}/review`, `/releases`). GitHub Actions runs API and public website tests. The public sandbox uses a secure, session-scoped cookie and keeps test artifacts in memory only; submitted test text is not persisted. PostgreSQL is used for consented partnership enquiries and opt-in anonymous usage events. A tenant-authenticated durable evidence mode is not yet enabled.

## What is deliberately NOT built yet (and why)

Per the strategy doc's validation gates — none of this should be built
before you have paying pilots and a changed production decision:

- Tenant-authenticated durable evidence mode, tenant-scoped authorization and a real Postgres create → restart → restore verification
- Real LLM judge (currently a transparent lexical-overlap stand-in in
  `app/services/evaluator.py::reference_judge` — replace with an actual
  model call behind the same `JudgeFn` signature, and add a second,
  independent judge before trusting disagreement checks)
- Production-grade authentication/authorization, CI/CD webhooks, drift watch, SDKs
- Any of the "10 organizations use this scenario library" scale — this
  scaffold ships with 10 illustrative scenarios, not a production library

## Honest next step

Point this at one real (or realistic mocked) customer AI endpoint, load
scenarios drawn from that customer's actual policies and one real
production failure, and see if the Release Record it produces would
actually change someone's release decision. That's Gate 4 from the
strategy doc — everything else waits for it.
