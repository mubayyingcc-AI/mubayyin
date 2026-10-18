"""
Mubayyin HTTP API — sandbox release-assurance engine and public test lab.
Durable evidence storage is enabled when DATABASE_URL is configured, but
authentication and tenant isolation are not yet implemented. Do not submit
confidential or production customer data.
"""
from __future__ import annotations

from pathlib import Path
import secrets
import json
from dataclasses import asdict
from enum import Enum
from typing import Optional

from fastapi import FastAPI, HTTPException, Header, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
import os
import re
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from app.models.core import AISystem, ScenarioCase, HumanReview, Severity, DeterministicCheckResult, JudgeScore, TrialResult, ReleaseRecord, ReleaseStatus
from app.services.evaluator import run_trial
from app.services.release_gate import decide_release, ReleaseThresholds

app = FastAPI(
    title="Mubayyin Release Assurance API",
    description="Vendor-neutral AI release-assurance engine — GCC beachhead.",
    version="0.2.0",
)

# --- in-memory trial storage (still sandbox-only; persistent trial storage is not implemented) ---
_systems: dict[str, AISystem] = {}
_scenarios: dict[str, ScenarioCase] = {}
_release_records: dict[str, list] = {}
_trial_results: dict[str, object] = {}
# Explicit provenance prevents results from one system being reused for another.
_trial_system_ids: dict[str, str] = {}

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



# --- persistent design-partner intake ----------------------------------------
# This table stores only voluntary partnership enquiries, not test payloads.
DATABASE_URL = os.getenv("DATABASE_URL", "")
PARTNER_ADMIN_TOKEN = os.getenv("PARTNER_ADMIN_TOKEN", "")
_db_engine = None
_database_ready = False
_database_error = None


def _database_url() -> str:
    url = DATABASE_URL.strip()
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if url.startswith("postgresql://") and "+" not in url.split(":", 1)[0]:
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


def _initialize_partner_storage() -> None:
    global _db_engine, _database_ready, _database_error
    if not DATABASE_URL:
        _database_error = "DATABASE_URL is not configured"
        return
    try:
        _db_engine = create_engine(_database_url(), pool_pre_ping=True, pool_recycle=300)
        with _db_engine.begin() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS mubayyin_partner_enquiries (
                    id BIGSERIAL PRIMARY KEY,
                    enquiry_id VARCHAR(40) NOT NULL UNIQUE,
                    name VARCHAR(120) NOT NULL,
                    email VARCHAR(254) NOT NULL,
                    organization VARCHAR(160) NOT NULL,
                    role VARCHAR(120) NOT NULL,
                    jurisdiction VARCHAR(80) NOT NULL,
                    workflow_type VARCHAR(120) NOT NULL,
                    current_problem TEXT NOT NULL,
                    preferred_involvement VARCHAR(80) NOT NULL,
                    consent_to_contact BOOLEAN NOT NULL DEFAULT FALSE,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
            """))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_mubayyin_partner_enquiries_created_at ON mubayyin_partner_enquiries (created_at DESC)"))
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS mubayyin_evidence_records (
                    record_type VARCHAR(24) NOT NULL,
                    record_id VARCHAR(80) NOT NULL,
                    system_id VARCHAR(80) NOT NULL,
                    payload TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    PRIMARY KEY (record_type, record_id)
                )
            """))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_mubayyin_evidence_system_created ON mubayyin_evidence_records (system_id, created_at)"))
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS mubayyin_usage_events (
                    id BIGSERIAL PRIMARY KEY,
                    visitor_id VARCHAR(36) NOT NULL,
                    event_name VARCHAR(40) NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
            """))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_mubayyin_usage_events_visitor_created ON mubayyin_usage_events (visitor_id, created_at DESC)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_mubayyin_usage_events_name_created ON mubayyin_usage_events (event_name, created_at DESC)"))
        _database_ready = True
        _database_error = None
    except Exception as exc:
        _database_ready = False
        # Keep secrets and connection strings out of logs and responses.
        _database_error = type(exc).__name__


class PartnerEnquiryRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: str = Field(min_length=5, max_length=254)
    organization: str = Field(min_length=2, max_length=160)
    role: str = Field(min_length=2, max_length=120)
    jurisdiction: str = Field(min_length=2, max_length=80)
    workflow_type: str = Field(min_length=2, max_length=120)
    current_problem: str = Field(min_length=20, max_length=3000)
    preferred_involvement: str = Field(min_length=2, max_length=80)
    consent_to_contact: bool
    website: str = ""  # honeypot: must remain empty


def _json_default(value):
    if isinstance(value, Enum):
        return value.value
    if hasattr(value, "__dict__"):
        return value.__dict__
    raise TypeError(f"Unsupported evidence value: {type(value).__name__}")


def _persist_evidence(record_type: str, record_id: str, system_id: str, record, immutable: bool = False) -> bool:
    """Persist evidence when the configured database is available.
    Returns False only in explicit local/test memory-only mode.
    """
    if not _database_ready or _db_engine is None:
        if DATABASE_URL:
            raise HTTPException(status_code=503, detail="Evidence storage is unavailable; no durable record was confirmed.")
        return False
    payload = json.dumps(asdict(record), sort_keys=True, separators=(",", ":"), default=_json_default)
    try:
        with _db_engine.begin() as conn:
            if immutable:
                conn.execute(text("""
                    INSERT INTO mubayyin_evidence_records (record_type, record_id, system_id, payload)
                    VALUES (:record_type, :record_id, :system_id, :payload)
                    ON CONFLICT (record_type, record_id) DO NOTHING
                """), {"record_type": record_type, "record_id": record_id, "system_id": system_id, "payload": payload})
            else:
                conn.execute(text("""
                    INSERT INTO mubayyin_evidence_records (record_type, record_id, system_id, payload)
                    VALUES (:record_type, :record_id, :system_id, :payload)
                    ON CONFLICT (record_type, record_id) DO UPDATE
                    SET payload = EXCLUDED.payload, system_id = EXCLUDED.system_id
                """), {"record_type": record_type, "record_id": record_id, "system_id": system_id, "payload": payload})
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail="Evidence storage failed; no durable record was confirmed.")
    return True


def _restore_evidence_records() -> None:
    global _database_ready, _database_error
    if not _database_ready or _db_engine is None:
        return
    try:
        with _db_engine.begin() as conn:
            rows = conn.execute(text("""
                SELECT record_type, record_id, system_id, payload
                FROM mubayyin_evidence_records ORDER BY created_at ASC
            """)).mappings().all()
        for row in rows:
            payload = json.loads(row["payload"])
            kind = row["record_type"]
            if kind == "system":
                _systems[row["record_id"]] = AISystem(**payload)
            elif kind == "scenario":
                _scenarios[row["record_id"]] = ScenarioCase(**payload)
            elif kind == "trial":
                review = payload.get("human_review")
                if review:
                    review["override_severity"] = Severity(review["override_severity"]) if review.get("override_severity") else None
                    payload["human_review"] = HumanReview(**review)
                payload["deterministic_checks"] = [DeterministicCheckResult(**x) for x in payload.get("deterministic_checks", [])]
                payload["judge_scores"] = [JudgeScore(**{**x, "severity": Severity(x["severity"])}) for x in payload.get("judge_scores", [])]
                payload["final_severity"] = Severity(payload["final_severity"])
                _trial_results[row["record_id"]] = TrialResult(**payload)
                _trial_system_ids[row["record_id"]] = row["system_id"]
            elif kind == "release":
                payload["status"] = ReleaseStatus(payload["status"])
                record = ReleaseRecord(**payload)
                _release_records.setdefault(row["system_id"], []).append(record)
    except Exception as exc:
        _database_ready = False
        _database_error = type(exc).__name__


@app.on_event("startup")
def initialize_storage():
    _initialize_partner_storage()
    _restore_evidence_records()


@app.post("/partnership/enquiries", status_code=201)
def create_partner_enquiry(req: PartnerEnquiryRequest):
    if req.website.strip():
        # Do not reveal the honeypot to bots; return a generic accepted response.
        return {"accepted": True, "enquiry_id": "received"}
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", req.email.strip()):
        raise HTTPException(status_code=422, detail="Enter a valid email address.")
    if not req.consent_to_contact:
        raise HTTPException(status_code=422, detail="Please consent to being contacted about this enquiry.")
    allowed_involvement = {"design_partner", "technical_evaluator", "research_collaborator", "other"}
    if req.preferred_involvement not in allowed_involvement:
        raise HTTPException(status_code=422, detail="Select a listed partnership type.")
    if not _database_ready or _db_engine is None:
        raise HTTPException(status_code=503, detail="Partnership enquiries are temporarily unavailable because persistent storage is not ready. Please try again later.")
    enquiry_id = "partner_" + __import__("uuid").uuid4().hex[:12]
    try:
        with _db_engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO mubayyin_partner_enquiries
                (enquiry_id, name, email, organization, role, jurisdiction, workflow_type,
                 current_problem, preferred_involvement, consent_to_contact)
                VALUES
                (:enquiry_id, :name, :email, :organization, :role, :jurisdiction, :workflow_type,
                 :current_problem, :preferred_involvement, :consent_to_contact)
            """), {
                "enquiry_id": enquiry_id,
                "name": req.name.strip(),
                "email": req.email.strip().lower(),
                "organization": req.organization.strip(),
                "role": req.role.strip(),
                "jurisdiction": req.jurisdiction.strip(),
                "workflow_type": req.workflow_type.strip(),
                "current_problem": req.current_problem.strip(),
                "preferred_involvement": req.preferred_involvement,
                "consent_to_contact": req.consent_to_contact,
            })
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail="We could not safely save this enquiry. No enquiry was confirmed; please retry later.")
    return {"accepted": True, "enquiry_id": enquiry_id, "message": "Your partnership enquiry was saved. Mubayyin is an early-access test lab; this is not a commercial commitment."}



# Privacy-minimised product analytics: only accepted event names, a random
# browser-generated ID, and timestamp. Never accept response text or PII.
class UsageEventRequest(BaseModel):
    visitor_id: str = Field(min_length=36, max_length=36)
    event_name: str = Field(min_length=3, max_length=40)


_ALLOWED_USAGE_EVENTS = {
    "lab_started", "trial_completed", "release_record_created",
    "retest_started", "journey_completed", "return_visit",
    "partner_form_started", "partner_form_submitted"
}


@app.post("/usage/events", status_code=202)
def record_usage_event(req: UsageEventRequest):
    if not re.fullmatch(r"[0-9a-fA-F-]{36}", req.visitor_id):
        raise HTTPException(status_code=422, detail="Invalid anonymous visitor identifier.")
    if req.event_name not in _ALLOWED_USAGE_EVENTS:
        raise HTTPException(status_code=422, detail="Unsupported usage event.")
    if not _database_ready or _db_engine is None:
        # Analytics must never break the test experience if storage is unavailable.
        return {"accepted": False, "reason": "analytics_storage_unavailable"}
    try:
        with _db_engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO mubayyin_usage_events (visitor_id, event_name)
                VALUES (:visitor_id, :event_name)
            """), {"visitor_id": req.visitor_id.lower(), "event_name": req.event_name})
        return {"accepted": True}
    except SQLAlchemyError:
        return {"accepted": False, "reason": "analytics_storage_unavailable"}


@app.get("/partner-inbox/usage")
def partner_usage_summary(
    authorization: Optional[str] = Header(default=None),
):
    if not PARTNER_ADMIN_TOKEN:
        raise HTTPException(status_code=503, detail="Usage analytics access is not configured.")
    expected = "Bearer " + PARTNER_ADMIN_TOKEN
    if not authorization or not secrets.compare_digest(authorization, expected):
        raise HTTPException(status_code=401, detail="Valid bearer token required.")
    if not _database_ready or _db_engine is None:
        raise HTTPException(status_code=503, detail="Usage analytics storage is unavailable.")
    try:
        with _db_engine.connect() as conn:
            totals = conn.execute(text("""
                SELECT event_name, COUNT(*) AS event_count,
                       COUNT(DISTINCT visitor_id) AS unique_visitors
                FROM mubayyin_usage_events
                WHERE created_at >= NOW() - INTERVAL '30 days'
                GROUP BY event_name ORDER BY event_name
            """)).mappings().all()
            returning = conn.execute(text("""
                SELECT COUNT(*) FROM (
                    SELECT visitor_id FROM mubayyin_usage_events
                    WHERE created_at >= NOW() - INTERVAL '30 days'
                    GROUP BY visitor_id HAVING COUNT(DISTINCT DATE(created_at)) >= 2
                ) AS returning_visitors
            """)).scalar_one()
        return {
            "window_days": 30,
            "returning_visitors_on_multiple_days": int(returning),
            "events": [dict(row) for row in totals],
            "definition": "A returning visitor is an opted-in anonymous browser ID with events on at least two distinct calendar dates in the last 30 days. This is a product-use signal, not proof of customer retention or paid retention."
        }
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail="Could not retrieve usage analytics.")

@app.get("/partner-inbox", include_in_schema=False)
def partner_inbox_page():
    response = FileResponse(Path(__file__).parent / "static" / "partner-inbox.html", media_type="text/html")
    response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/partnership/enquiries")
def list_partner_enquiries(
    authorization: Optional[str] = Header(default=None),
    limit: int = Query(default=50, ge=1, le=200),
):
    if not PARTNER_ADMIN_TOKEN:
        raise HTTPException(status_code=503, detail="Partner inbox access is not configured. Set PARTNER_ADMIN_TOKEN in the service environment.")
    expected = "Bearer " + PARTNER_ADMIN_TOKEN
    if not authorization or not secrets.compare_digest(authorization, expected):
        raise HTTPException(status_code=401, detail="Valid bearer token required.")
    if not _database_ready or _db_engine is None:
        raise HTTPException(status_code=503, detail="Partnership storage is unavailable.")
    try:
        with _db_engine.connect() as conn:
            rows = conn.execute(text("""
                SELECT enquiry_id, name, email, organization, role, jurisdiction,
                       workflow_type, current_problem, preferred_involvement, created_at
                FROM mubayyin_partner_enquiries
                ORDER BY created_at DESC
                LIMIT :limit
            """), {"limit": limit}).mappings().all()
        return {"enquiries": [
            {**dict(row), "created_at": row["created_at"].isoformat() if row["created_at"] else None}
            for row in rows
        ]}
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail="Could not retrieve enquiries from persistent storage.")

@app.get("/", include_in_schema=False)
def website():
    return FileResponse(Path(__file__).parent / "static" / "index.html", media_type="text/html")


@app.post("/systems")
def create_system(req: CreateSystemRequest):
    system = AISystem(**req.dict())
    durable = _persist_evidence("system", system.system_id, system.system_id, system)
    _systems[system.system_id] = system
    return {"system_id": system.system_id, "config_hash": system.config_hash(), "persistence": "durable" if durable else "memory_only"}


@app.post("/scenarios")
def create_scenario(req: CreateScenarioRequest):
    scenario = ScenarioCase(**req.dict())
    durable = _persist_evidence("scenario", scenario.scenario_id, "scenario:" + scenario.scenario_id, scenario)
    _scenarios[scenario.scenario_id] = scenario
    return {"scenario_id": scenario.scenario_id, "persistence": "durable" if durable else "memory_only"}


@app.post("/trials")
def run_trial_endpoint(req: RunTrialRequest):
    system = _systems.get(req.system_id)
    scenario = _scenarios.get(req.scenario_id)
    if not system or not scenario:
        raise HTTPException(status_code=404, detail="system or scenario not found")

    result = run_trial(scenario, req.model_output)
    result.system_config_hash = system.config_hash()
    durable = _persist_evidence("trial", result.result_id, system.system_id, result)
    _trial_results[result.result_id] = result
    _trial_system_ids[result.result_id] = system.system_id
    return {
        "result_id": result.result_id,
        "final_severity": result.final_severity.value,
        "is_failure": result.is_failure(),
        "deterministic_checks": [c.__dict__ for c in result.deterministic_checks],
        "judge_scores": [
            {
                "judge_name": score.judge_name,
                "groundedness": score.groundedness,
                "policy_adherence": score.policy_adherence,
                "language_quality": score.language_quality,
                "escalation_quality": score.escalation_quality,
                "privacy_behavior": score.privacy_behavior,
                "severity": score.severity.value,
                "reason": score.reason,
            }
            for score in result.judge_scores
        ],
        "system_config_hash": result.system_config_hash,
        "persistence": "durable" if durable else "memory_only",
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
    system_id = _trial_system_ids.get(result_id)
    if not system_id:
        raise HTTPException(status_code=409, detail="Trial provenance is missing; this result cannot be safely updated.")
    durable = _persist_evidence("trial", result.result_id, system_id, result)
    return {"result_id": result_id, "reviewed": True, "persistence": "durable" if durable else "memory_only"}


@app.post("/releases")
def create_release(req: DecideReleaseRequest):
    system = _systems.get(req.system_id)
    if not system:
        raise HTTPException(status_code=404, detail="system not found")

    if not req.result_ids:
        raise HTTPException(status_code=400, detail="at least one trial result is required")
    if len(req.result_ids) != len(set(req.result_ids)):
        raise HTTPException(status_code=422, detail="duplicate trial result IDs are not allowed")
    missing_ids = [rid for rid in req.result_ids if rid not in _trial_results]
    if missing_ids:
        raise HTTPException(status_code=404, detail="one or more trial results were not found; no release record was created")

    results = [_trial_results[rid] for rid in req.result_ids]
    for result in results:
        if _trial_system_ids.get(result.result_id) != req.system_id:
            raise HTTPException(status_code=409, detail="trial provenance mismatch: every result must belong to the requested AI system")
        if result.system_config_hash != system.config_hash():
            raise HTTPException(status_code=409, detail="stale evidence: the AI system configuration changed after this trial. Rerun affected scenarios before creating a release record.")

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
    durable = _persist_evidence("release", record.record_id, system.system_id, record, immutable=True)
    history.append(record)
    payload = record.to_dict()
    payload["persistence"] = "durable" if durable else "memory_only"
    return payload


@app.get("/releases/{system_id}")
def get_release_history(system_id: str):
    history = _release_records.get(system_id, [])
    if not history:
        raise HTTPException(status_code=404, detail="no release records for this system")
    return [r.to_dict() for r in history]


@app.get("/health")
def health():
    return {"status": "ok", "version": app.version, "partner_storage": "ready" if _database_ready else "unavailable"}
