"""
Mubayyin HTTP API — verified core engine plus the public test-lab website.
The current API stores records in memory; do not submit confidential or
production customer data until persistence, access controls, and tenant
isolation have been implemented and reviewed.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.models.core import AISystem, ScenarioCase, HumanReview, Severity
from app.services.evaluator import run_trial
from app.services.release_gate import decide_release, ReleaseThresholds

app = FastAPI(
    title="Mubayyin Release Assurance API",
    description="Vendor-neutral AI release-assurance engine — GCC beachhead.",
    version="0.2.0",
)

# --- in-memory storage (replace with persistent, tenant-isolated storage) ---
_systems: dict[str, AISystem] = {}
_scenarios: dict[str, ScenarioCase] = {}
_release_records: dict[str, list] = {}
_trial_results: dict[str, object] = {}

# --- request/response schemas -------------------------------------------------
class CreateSystemRequest(BaseModel):
    system_id: str
    name: str
    organization: str
    jurisdiction: str
    model_provider: str
    model_version: str
    prompt_version: str
    retrieval_version: Optional[str] = None
    policy_version: str = "v1"
    tool_version: Optional[str] = None


class CreateScenarioRequest(BaseModel):
    scenario_id: str
    language: str
    dialect: Optional[str] = None
    category: str
    risk_level: str
    user_input: str
    expected_behavior: str
    forbidden_behavior: Optional[str] = None
    requires_escalation: bool = False
    required_disclosure: Optional[str] = None
    source: str = "synthetic"


class RunTrialRequest(BaseModel):
    system_id: str
    scenario_id: str
    model_output: str


class HumanReviewRequest(BaseModel):
    reviewer: str
    agrees_with_automation: bool
    override_severity: Optional[str] = None
    comment: str = ""


class DecideReleaseRequest(BaseModel):
    system_id: str
    result_ids: list[str]
    approver: Optional[str] = None
    max_critical_failures: int = 0
    max_major_failures: int = 3
    scenario_set_version: str = "v1"


@app.get("/", include_in_schema=False)
def website():
    return FileResponse(Path(__file__).parent / "static" / "index.html", media_type="text/html")


@app.post("/systems")
def create_system(req: CreateSystemRequest):
    system = AISystem(**req.dict())
    _systems[system.system_id] = system
    return {"system_id": system.system_id, "config_hash": system.config_hash()}


@app.post("/scenarios")
def create_scenario(req: CreateScenarioRequest):
    scenario = ScenarioCase(**req.dict())
    _scenarios[scenario.scenario_id] = scenario
    return {"scenario_id": scenario.scenario_id}


@app.post("/trials")
def run_trial_endpoint(req: RunTrialRequest):
    system = _systems.get(req.system_id)
    scenario = _scenarios.get(req.scenario_id)
    if not system or not scenario:
        raise HTTPException(status_code=404, detail="system or scenario not found")

    result = run_trial(scenario, req.model_output)
    result.system_config_hash = system.config_hash()
    _trial_results[result.result_id] = result
    return {
        "result_id": result.result_id,
        "final_severity": result.final_severity.value,
        "is_failure": result.is_failure(),
        "deterministic_checks": [c.__dict__ for c in result.deterministic_checks],
    }


@app.post("/trials/{result_id}/review")
def add_human_review(result_id: str, req: HumanReviewRequest):
    result = _trial_results.get(result_id)
    if not result:
        raise HTTPException(status_code=404, detail="trial result not found")
    result.human_review = HumanReview(
        reviewer=req.reviewer,
        agrees_with_automation=req.agrees_with_automation,
        override_severity=Severity(req.override_severity) if req.override_severity else None,
        comment=req.comment,
    )
    return {"result_id": result_id, "reviewed": True}


@app.post("/releases")
def create_release(req: DecideReleaseRequest):
    system = _systems.get(req.system_id)
    if not system:
        raise HTTPException(status_code=404, detail="system not found")

    results = [_trial_results[rid] for rid in req.result_ids if rid in _trial_results]
    if not results:
        raise HTTPException(status_code=400, detail="no valid trial results provided")

    history = _release_records.setdefault(req.system_id, [])
    previous_hash = history[-1].evidence_hash if history else None
    record = decide_release(
        system=system,
        results=results,
        thresholds=ReleaseThresholds(
            max_critical_failures=req.max_critical_failures,
            max_major_failures=req.max_major_failures,
        ),
        approver=req.approver,
        previous_record_hash=previous_hash,
        scenario_set_version=req.scenario_set_version,
    )
    history.append(record)
    return record.to_dict()


@app.get("/releases/{system_id}")
def get_release_history(system_id: str):
    history = _release_records.get(system_id, [])
    if not history:
        raise HTTPException(status_code=404, detail="no release records for this system")
    return [r.to_dict() for r in history]


@app.get("/health")
def health():
    return {"status": "ok", "version": app.version}
