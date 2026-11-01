"""Tenant-scoped API routes for the five research assurance workstreams."""
from datetime import datetime, timezone
import uuid
from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Query
from pydantic import BaseModel, Field

from app.services.assurance_workstreams import run_five_workstream_assessment, build_retest_event

router = APIRouter(prefix="/tenant/assurance", tags=["tenant-assurance"])

class AssuranceAssessmentRequest(BaseModel):
    system_id: str = Field(min_length=1, max_length=80)
    output: str = Field(min_length=1, max_length=20000)
    required_terms: list[str] = Field(default_factory=list, max_length=40)
    prohibited_terms: list[str] = Field(default_factory=list, max_length=40)
    required_values: list[str] = Field(default_factory=list, max_length=40)
    language_context: str = Field(default="ar-en", max_length=40)
    baseline_run: Optional[dict] = None
    candidate_run: Optional[dict] = None
    require_human_approval: bool = False
    scenario_set_version: str = Field(default="unversioned", max_length=80)

class RetestEventRequest(BaseModel):
    system_id: str = Field(min_length=1, max_length=80)
    previous_snapshot_hash: str = Field(default="", max_length=128)
    current_snapshot_hash: str = Field(min_length=1, max_length=128)
    changed_components: list[str] = Field(min_length=1, max_length=40)

@router.post("/assessments", status_code=201)
def create_assessment(req: AssuranceAssessmentRequest, authorization: Optional[str] = Header(default=None)):
    from app.api import _require_tenant, _tenant_get, _tenant_store
    from app.api import _json_default
    tenant_id = _require_tenant(authorization)
    system = _tenant_get(tenant_id, "system", req.system_id)
    if not system:
        raise HTTPException(404, "Tenant system not found.")
    snapshot_hash = system.config_hash()
    result = run_five_workstream_assessment(
        output=req.output, required_terms=req.required_terms,
        prohibited_terms=req.prohibited_terms, required_values=req.required_values,
        language_context=req.language_context, baseline_run=req.baseline_run,
        candidate_run=req.candidate_run, evidence_complete=False,
        require_human_approval=req.require_human_approval,
        system_snapshot_hash=snapshot_hash,
        scenario_set_version=req.scenario_set_version,
        policy_version=system.policy_version,
        issuer="tenant-authenticated-customer-runner",
    )
    assessment_id = "rda_" + uuid.uuid4().hex
    record = {
        "assessment_id": assessment_id, "tenant_id": tenant_id,
        "system_id": system.system_id, "system_snapshot_hash": snapshot_hash,
        "scenario_set_version": req.scenario_set_version,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source": "tenant-authenticated-customer-runner",
        "assessment": result,
        "notice": "Research assessment only; does not create or approve a Release Record.",
    }
    _tenant_store(tenant_id, "rd_assessment", assessment_id, system.system_id, record, immutable=True)
    return {**record, "persistence": "durable"}

@router.get("/assessments/{assessment_id}")
def get_assessment(assessment_id: str, authorization: Optional[str] = Header(default=None)):
    from app.api import _require_tenant, _tenant_get
    tenant_id = _require_tenant(authorization)
    record = _tenant_get(tenant_id, "rd_assessment", assessment_id)
    if not record:
        raise HTTPException(404, "Tenant assurance assessment not found.")
    return {**record, "persistence": "durable"}

@router.post("/retests", status_code=201)
def create_retest(req: RetestEventRequest, authorization: Optional[str] = Header(default=None)):
    from app.api import _require_tenant, _tenant_get, _tenant_store
    tenant_id = _require_tenant(authorization)
    system = _tenant_get(tenant_id, "system", req.system_id)
    if not system:
        raise HTTPException(404, "Tenant system not found.")
    current_hash = system.config_hash()
    if req.current_snapshot_hash != current_hash:
        raise HTTPException(409, "Current snapshot hash does not match tenant system configuration.")
    event = build_retest_event(
        tenant_ref=tenant_id, system_ref=system.system_id,
        previous_snapshot_hash=req.previous_snapshot_hash,
        current_snapshot_hash=current_hash, changed_components=req.changed_components,
    )
    existing = _tenant_get(tenant_id, "rd_retest_event", event["event_id"])
    if existing:
        return {**existing, "persistence": "durable", "duplicate": True}
    record = {
        **event, "created_at": datetime.now(timezone.utc).isoformat(),
        "dispatch_status": "recorded_not_dispatched",
        "notice": "Durable event record only; no background queue or automatic retest is enabled.",
    }
    _tenant_store(tenant_id, "rd_retest_event", event["event_id"], system.system_id, record, immutable=True)
    return {**record, "persistence": "durable", "duplicate": False}

@router.get("/retests")
def list_retests(authorization: Optional[str] = Header(default=None), limit: int = Query(default=50, ge=1, le=200)):
    from app.api import _require_tenant, _tenant_list
    tenant_id = _require_tenant(authorization)
    records = _tenant_list(tenant_id, "rd_retest_event")
    selected = records[-limit:]
    return {"events": [record for _, _, record in selected], "count": len(selected), "persistence": "durable"}
