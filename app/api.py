"""Mubayyin HTTP API — verified core engine and public GCC test lab."""
from __future__ import annotations
from pathlib import Path
import secrets, json, os, re, uuid, hashlib, time
from dataclasses import asdict
from enum import Enum
from typing import Optional
from fastapi import FastAPI, HTTPException, Header, Query, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from app.models.core import AISystem, ScenarioCase, HumanReview, Severity, DeterministicCheckResult, JudgeScore, TrialResult, ReleaseRecord, ReleaseStatus
from app.services.evaluator import run_trial
from app.services.release_gate import decide_release, ReleaseThresholds
from app.services.attestation import create_release_bundle, verify_release_bundle
app=FastAPI(title="Mubayyin Release Assurance API",description="Vendor-neutral AI release-assurance engine — GCC beachhead.",version="0.2.0")
_systems={};_scenarios={};_release_records={};_trial_results={};_trial_system_ids={};_system_sessions={};_scenario_sessions={};_trial_sessions={};_release_sessions={};_session_last_seen={};_last_session_prune=0
class CreateSystemRequest(BaseModel):
 system_id:str=Field(min_length=1,max_length=80);name:str=Field(min_length=1,max_length=120);organization:str=Field(min_length=1,max_length=120);jurisdiction:str=Field(min_length=2,max_length=40);model_provider:str=Field(min_length=1,max_length=80);model_version:str=Field(min_length=1,max_length=80);prompt_version:str=Field(min_length=1,max_length=80);retrieval_version:Optional[str]=Field(default=None,max_length=80);policy_version:str=Field(default="v1",max_length=80);tool_version:Optional[str]=Field(default=None,max_length=80)
class CreateScenarioRequest(BaseModel):
 scenario_id:str=Field(min_length=1,max_length=80);language:str=Field(min_length=2,max_length=8);dialect:Optional[str]=Field(default=None,max_length=40);category:str=Field(min_length=1,max_length=80);risk_level:str=Field(min_length=1,max_length=20);user_input:str=Field(min_length=1,max_length=4000);expected_behavior:str=Field(min_length=1,max_length=4000);forbidden_behavior:Optional[str]=Field(default=None,max_length=1000);requires_escalation:bool=False;required_disclosure:Optional[str]=Field(default=None,max_length=1000);source:str=Field(default="synthetic",max_length=40)
class RunTrialRequest(BaseModel): system_id:str=Field(min_length=1,max_length=80);scenario_id:str=Field(min_length=1,max_length=80);model_output:str=Field(min_length=1,max_length=20000)
class HumanReviewRequest(BaseModel): reviewer:str;agrees_with_automation:bool;override_severity:Optional[str]=None;comment:str=""
class DecideReleaseRequest(BaseModel): system_id:str;result_ids:list[str];approver:Optional[str]=None;max_critical_failures:int=0;max_major_failures:int=3;scenario_set_version:str="v1";required_scenario_ids:list[str]=Field(default_factory=list)
DATABASE_URL=os.getenv("DATABASE_URL","");PARTNER_ADMIN_TOKEN=os.getenv("PARTNER_ADMIN_TOKEN","");_db_engine=None;_database_ready=False;_database_error=None
def _prune_expired_sandbox_sessions():
 global _last_session_prune
 now=time.time()
 if now-_last_session_prune<60:return
 _last_session_prune=now
 expired={sid for sid,last in _session_last_seen.items() if now-last>7200}
 for sid in expired:
  for key,owner in list(_system_sessions.items()):
   if owner==sid:_system_sessions.pop(key,None);_systems.pop(key,None);_release_records.pop(key,None)
  for key,owner in list(_scenario_sessions.items()):
   if owner==sid:_scenario_sessions.pop(key,None);_scenarios.pop(key,None)
  for key,owner in list(_trial_sessions.items()):
   if owner==sid:
    _trial_sessions.pop(key,None);_trial_system_ids.pop(key,None);_trial_results.pop(key,None)
  for key,owner in list(_release_sessions.items()):
   if owner==sid:_release_sessions.pop(key,None)
  for system_id,history in list(_release_records.items()):
   kept=[rec for rec in history if _release_sessions.get(rec.record_id)!=sid]
   if kept:_release_records[system_id]=kept
   else:_release_records.pop(system_id,None)
  _session_last_seen.pop(sid,None)

def _touch_sandbox_session(sid:str):
 _prune_expired_sandbox_sessions()
 _session_last_seen[sid]=time.time()

def _require_sandbox_session(request:Request)->str:
 sid=request.cookies.get("mubayyin_sandbox_session")
 try:uuid.UUID(sid or "")
 except (ValueError,AttributeError):raise HTTPException(401,"Open the Mubayyin lab page first to create a private sandbox session.")
 _touch_sandbox_session(sid)
 return sid

def _set_sandbox_cookie(request:Request,response:Response)->str:
 sid=request.cookies.get("mubayyin_sandbox_session")
 try:uuid.UUID(sid or "")
 except (ValueError,AttributeError):
  sid=str(uuid.uuid4())
  response.set_cookie("mubayyin_sandbox_session",sid,max_age=7200,httponly=True,secure=request.url.scheme=="https",samesite="strict",path="/")
 _touch_sandbox_session(sid)
 return sid

def _database_url():
 u=DATABASE_URL.strip()
 if u.startswith("postgres://"):u="postgresql://"+u[10:]
 if u.startswith("postgresql://") and "+" not in u.split(":",1)[0]:u=u.replace("postgresql://","postgresql+psycopg://",1)
 return u
def _initialize_storage():
 global _db_engine,_database_ready,_database_error
 if not DATABASE_URL:_database_error="DATABASE_URL is not configured";return
 try:
  _db_engine=create_engine(_database_url(),pool_pre_ping=True,pool_recycle=300)
  with _db_engine.begin() as c:
   c.execute(text("CREATE TABLE IF NOT EXISTS mubayyin_partner_enquiries (id BIGSERIAL PRIMARY KEY,enquiry_id VARCHAR(40) UNIQUE NOT NULL,name VARCHAR(120) NOT NULL,email VARCHAR(254) NOT NULL,organization VARCHAR(160) NOT NULL,role VARCHAR(120) NOT NULL,jurisdiction VARCHAR(80) NOT NULL,workflow_type VARCHAR(120) NOT NULL,current_problem TEXT NOT NULL,preferred_involvement VARCHAR(80) NOT NULL,consent_to_contact BOOLEAN NOT NULL DEFAULT FALSE,created_at TIMESTAMPTZ NOT NULL DEFAULT NOW())"))
   c.execute(text("CREATE INDEX IF NOT EXISTS idx_partner_created ON mubayyin_partner_enquiries(created_at DESC)"))
   c.execute(text("CREATE TABLE IF NOT EXISTS mubayyin_evidence_records (record_type VARCHAR(24) NOT NULL,record_id VARCHAR(80) NOT NULL,system_id VARCHAR(80) NOT NULL,payload TEXT NOT NULL,created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),PRIMARY KEY(record_type,record_id))"))
   c.execute(text("CREATE TABLE IF NOT EXISTS mubayyin_usage_events (id BIGSERIAL PRIMARY KEY,visitor_id VARCHAR(36) NOT NULL,event_name VARCHAR(40) NOT NULL,created_at TIMESTAMPTZ NOT NULL DEFAULT NOW())"))
  _database_ready=True;_database_error=None
 except Exception as e:_database_ready=False;_database_error=type(e).__name__
def _json_default(v):
 if isinstance(v,Enum):return v.value
 if hasattr(v,"__dict__"):return v.__dict__
 raise TypeError(type(v).__name__)
def _restore_evidence_records():
 """Rehydrate typed in-memory objects from durable evidence rows on startup."""
 if not _database_ready or _db_engine is None:
  return
 try:
  with _db_engine.connect() as c:
   rows=c.execute(text("SELECT record_type,record_id,payload FROM mubayyin_evidence_records ORDER BY created_at ASC")).mappings().all()
  for row in rows:
   kind=row["record_type"];p=json.loads(row["payload"])
   if kind=="system":
    _systems[row["record_id"]]=AISystem(**p)
   elif kind=="scenario":
    _scenarios[row["record_id"]]=ScenarioCase(**p)
   elif kind=="trial":
    for key in ("deterministic_checks",):
     p[key]=[DeterministicCheckResult(**x) for x in p.get(key,[])]
    p["judge_scores"]=[JudgeScore(**{**x,"severity":Severity(x["severity"])}) for x in p.get("judge_scores",[])]
    if p.get("human_review"):
     hr=p["human_review"]
     p["human_review"]=HumanReview(**{**hr,"override_severity":Severity(hr["override_severity"]) if hr.get("override_severity") else None})
    p["final_severity"]=Severity(p["final_severity"])
    _trial_results[row["record_id"]]=TrialResult(**p)
    _trial_system_ids[row["record_id"]]=row["system_id"]
   elif kind=="release":
    p["status"]=ReleaseStatus(p["status"])
    rec=ReleaseRecord(**p)
    _release_records.setdefault(rec.system_id,[]).append(rec)
  for records in _release_records.values():
   records.sort(key=lambda r:r.created_at)
 except Exception as e:
  # A partial restore must never be advertised as ready for durable evidence.
  _database_error="evidence_restore_"+type(e).__name__
  raise RuntimeError("Mubayyin evidence restoration failed") from e

def _persist(kind,rid,sid,record,immutable=False):
 if not _database_ready or _db_engine is None:
  if DATABASE_URL:raise HTTPException(503,"Durable evidence storage is unavailable; no record was confirmed.")
  return False
 payload=json.dumps(asdict(record),sort_keys=True,separators=(",",":"),default=_json_default)
 try:
  with _db_engine.begin() as c:
   if immutable:c.execute(text("INSERT INTO mubayyin_evidence_records(record_type,record_id,system_id,payload) VALUES(:k,:r,:s,:p) ON CONFLICT(record_type,record_id) DO NOTHING"),dict(k=kind,r=rid,s=sid,p=payload))
   else:c.execute(text("INSERT INTO mubayyin_evidence_records(record_type,record_id,system_id,payload) VALUES(:k,:r,:s,:p) ON CONFLICT(record_type,record_id) DO UPDATE SET payload=EXCLUDED.payload,system_id=EXCLUDED.system_id"),dict(k=kind,r=rid,s=sid,p=payload))
 except SQLAlchemyError:raise HTTPException(503,"Evidence storage failed; no durable record was confirmed.")
 return True
@app.on_event("startup")
def startup():
 _initialize_storage()
 # Public sandbox evidence is session-scoped and ephemeral. Durable evidence restoration stays disabled until tenant-scoped authentication and authorization exist.
@app.get("/health",include_in_schema=False)
def health():
 return JSONResponse({"status":"ok","service":"mubayyin-web","version":app.version,"database":"ready" if _database_ready else ("not_configured" if not DATABASE_URL else "unavailable")})
@app.get("/ready",include_in_schema=False)
def ready():
 if DATABASE_URL and not _database_ready: raise HTTPException(503,"Database is configured but not ready.")
 return {"ready":True,"database":"ready" if _database_ready else "memory_only"}
class PartnerEnquiryRequest(BaseModel):
 name:str=Field(min_length=2,max_length=120);email:str=Field(min_length=5,max_length=254);organization:str=Field(min_length=2,max_length=160);role:str=Field(min_length=2,max_length=120);jurisdiction:str=Field(min_length=2,max_length=80);workflow_type:str=Field(min_length=2,max_length=120);current_problem:str=Field(min_length=20,max_length=3000);preferred_involvement:str=Field(min_length=2,max_length=80);consent_to_contact:bool;website:str=""
@app.post("/partnership/enquiries",status_code=201)
def create_partner(req:PartnerEnquiryRequest):
 if req.website.strip():return {"accepted":True,"enquiry_id":"received"}
 if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+",req.email.strip()):raise HTTPException(422,"Enter a valid email address.")
 if not req.consent_to_contact:raise HTTPException(422,"Please consent to being contacted about this enquiry.")
 if req.preferred_involvement not in {"design_partner","technical_evaluator","research_collaborator","other"}:raise HTTPException(422,"Select a listed partnership type.")
 if not _database_ready:raise HTTPException(503,"Partnership enquiries are temporarily unavailable because persistent storage is not ready.")
 eid="partner_"+__import__('uuid').uuid4().hex[:12]
 try:
  with _db_engine.begin() as c:c.execute(text("INSERT INTO mubayyin_partner_enquiries(enquiry_id,name,email,organization,role,jurisdiction,workflow_type,current_problem,preferred_involvement,consent_to_contact) VALUES(:id,:n,:e,:o,:r,:j,:w,:p,:i,:c)"),dict(id=eid,n=req.name.strip(),e=req.email.strip().lower(),o=req.organization.strip(),r=req.role.strip(),j=req.jurisdiction.strip(),w=req.workflow_type.strip(),p=req.current_problem.strip(),i=req.preferred_involvement,c=req.consent_to_contact))
 except SQLAlchemyError:raise HTTPException(503,"We could not safely save this enquiry.")
 return {"accepted":True,"enquiry_id":eid,"message":"Your partnership enquiry was saved."}
@app.get("/partner-inbox",include_in_schema=False)
def inbox():return FileResponse(Path(__file__).parent/"static"/"partner-inbox.html",media_type="text/html")
@app.get("/partnership/enquiries")
def list_partners(authorization:Optional[str]=Header(default=None),limit:int=Query(default=50,ge=1,le=200)):
 if not PARTNER_ADMIN_TOKEN:raise HTTPException(503,"Partner inbox access is not configured.")
 if not authorization or not secrets.compare_digest(authorization,"Bearer "+PARTNER_ADMIN_TOKEN):raise HTTPException(401,"Valid bearer token required.")
 if not _database_ready:raise HTTPException(503,"Partnership storage is unavailable.")
 with _db_engine.connect() as c:rows=c.execute(text("SELECT enquiry_id,name,email,organization,role,jurisdiction,workflow_type,current_problem,preferred_involvement,created_at FROM mubayyin_partner_enquiries ORDER BY created_at DESC LIMIT :limit"),{"limit":limit}).mappings().all()
 return {"enquiries":[{**dict(r),"created_at":r["created_at"].isoformat() if r["created_at"] else None} for r in rows]}
@app.get("/",include_in_schema=False)
def website(request:Request):
 response=FileResponse(Path(__file__).parent/"static"/"index.html",media_type="text/html")
 _set_sandbox_cookie(request,response)
 return response
@app.get("/ar",include_in_schema=False)
def arabic(request:Request):
 response=FileResponse(Path(__file__).parent/"static"/"arabic.html",media_type="text/html")
 _set_sandbox_cookie(request,response)
 return response
@app.post("/systems")
def system(req:CreateSystemRequest,request:Request):
 sid=_require_sandbox_session(request)
 s=AISystem(**req.dict())
 existing=_systems.get(s.system_id)
 if existing and _system_sessions.get(s.system_id)!=sid:raise HTTPException(404,"Sandbox system not found.")
 if existing and existing.config_hash()!=s.config_hash():raise HTTPException(409,"System ID already exists with a different configuration; create a new versioned system ID.")
 _systems[s.system_id]=s;_system_sessions[s.system_id]=sid
 # Public lab evidence is intentionally ephemeral: never persist arbitrary submitted model output.
 return {"system_id":s.system_id,"config_hash":s.config_hash(),"persistence":"memory_only"}
@app.post("/scenarios")
def scenario(req:CreateScenarioRequest,request:Request):
 sid=_require_sandbox_session(request)
 s=ScenarioCase(**req.dict())
 existing=_scenarios.get(s.scenario_id)
 if existing and _scenario_sessions.get(s.scenario_id)!=sid:raise HTTPException(404,"Sandbox scenario not found.")
 if existing and existing.config_hash()!=s.config_hash() and any(t.scenario_id==s.scenario_id for t in _trial_results.values()):
  raise HTTPException(409,"Scenario is already referenced by trial evidence; create a new scenario ID for changed requirements.")
 _scenarios[s.scenario_id]=s;_scenario_sessions[s.scenario_id]=sid
 return {"scenario_id":s.scenario_id,"scenario_config_hash":s.config_hash(),"persistence":"memory_only"}
@app.post("/trials")
def trial(req:RunTrialRequest,request:Request):
 sid=_require_sandbox_session(request)
 s=_systems.get(req.system_id);sc=_scenarios.get(req.scenario_id)
 if not s or not sc or _system_sessions.get(req.system_id)!=sid or _scenario_sessions.get(req.scenario_id)!=sid:raise HTTPException(404,"Sandbox system or scenario not found.")
 r=run_trial(sc,req.model_output);r.system_config_hash=s.config_hash();r.scenario_config_hash=sc.config_hash();_trial_results[r.result_id]=r;_trial_system_ids[r.result_id]=s.system_id;_trial_sessions[r.result_id]=sid
 return {"result_id":r.result_id,"final_severity":r.final_severity.value,"is_failure":r.is_failure(),"deterministic_checks":[c.__dict__ for c in r.deterministic_checks],"judge_scores":[{"judge_name":j.judge_name,"groundedness":j.groundedness,"policy_adherence":j.policy_adherence,"language_quality":j.language_quality,"escalation_quality":j.escalation_quality,"privacy_behavior":j.privacy_behavior,"severity":j.severity.value,"reason":j.reason} for j in r.judge_scores],"system_config_hash":r.system_config_hash,"scenario_config_hash":r.scenario_config_hash,"persistence":"memory_only"}
@app.post("/trials/{result_id}/review")
def review(result_id:str,req:HumanReviewRequest,request:Request):
 sid=_require_sandbox_session(request)
 r=_trial_results.get(result_id)
 if not r or _trial_sessions.get(result_id)!=sid:raise HTTPException(404,"Sandbox trial result not found.")
 if any(r.result_id in rec.trial_result_ids for records in _release_records.values() for rec in records):raise HTTPException(409,"This trial is already bound to an immutable Release Record; create a new trial and review it before a new release.")
 if not req.reviewer.strip():raise HTTPException(422,"Reviewer is required.")
 override=None
 if req.override_severity:
  try:override=Severity(req.override_severity)
  except ValueError:raise HTTPException(422,"Invalid override severity.")
 r.human_review=HumanReview(reviewer=req.reviewer.strip(),agrees_with_automation=req.agrees_with_automation,override_severity=override,comment=req.comment.strip())
 return {"result_id":r.result_id,"review_saved":True,"persistence":"memory_only"}

ALLOWED_USAGE_EVENTS={"trial_completed","release_record_created","retest_completed","partner_enquiry_started","language_switched"}
class UsageEventRequest(BaseModel):
 visitor_id:str=Field(min_length=36,max_length=36)
 event_name:str
@app.post("/usage/events",status_code=202)
def usage_event(req:UsageEventRequest):
 if req.event_name not in ALLOWED_USAGE_EVENTS:raise HTTPException(422,"Unknown usage event.")
 try:uuid.UUID(req.visitor_id)
 except ValueError:raise HTTPException(422,"visitor_id must be a UUID.")
 if not _database_ready or _db_engine is None:return JSONResponse(status_code=202,content={"accepted":False,"reason":"storage_unavailable"})
 try:
  with _db_engine.begin() as c:c.execute(text("INSERT INTO mubayyin_usage_events(visitor_id,event_name) VALUES(:v,:e)"),{"v":req.visitor_id,"e":req.event_name})
 except SQLAlchemyError:return JSONResponse(status_code=202,content={"accepted":False,"reason":"storage_unavailable"})
 return JSONResponse(status_code=202,content={"accepted":True})

@app.get("/partner-inbox/usage")
def partner_usage(authorization:Optional[str]=Header(default=None)):
 if not PARTNER_ADMIN_TOKEN:raise HTTPException(503,"Partner inbox access is not configured.")
 if not authorization or not secrets.compare_digest(authorization,"Bearer "+PARTNER_ADMIN_TOKEN):raise HTTPException(401,"Valid bearer token required.")
 if not _database_ready or _db_engine is None:raise HTTPException(503,"Usage storage is unavailable.")
 try:
  with _db_engine.connect() as c:
   events=c.execute(text("SELECT event_name,COUNT(*) AS event_count,COUNT(DISTINCT visitor_id) AS unique_visitors FROM mubayyin_usage_events WHERE created_at >= NOW() - INTERVAL '30 days' GROUP BY event_name ORDER BY event_name")).mappings().all()
   returning=c.execute(text("SELECT COUNT(*) FROM (SELECT visitor_id FROM mubayyin_usage_events WHERE created_at >= NOW() - INTERVAL '30 days' GROUP BY visitor_id HAVING COUNT(DISTINCT DATE(created_at)) >= 2) q")).scalar_one()
 except SQLAlchemyError:raise HTTPException(503,"Usage summary could not be read.")
 return {"events":[dict(x) for x in events],"returning_visitors_on_multiple_days":int(returning),"definition":"Anonymous visitor IDs with opt-in events on two or more distinct days in the last 30 days."}

@app.get("/releases/{record_id}/export")
def export_release_record(record_id:str,request:Request):
 """Download a portable Release Record bundle from the caller's own sandbox session."""
 sid=_require_sandbox_session(request)
 record=None
 for history in _release_records.values():
  for candidate in history:
   if candidate.record_id==record_id:
    record=candidate
    break
  if record is not None:break
 if record is None or _release_sessions.get(record_id)!=sid:
  raise HTTPException(404,"Sandbox Release Record not found.")
 trial_evidence=[]
 scenario_ids=set(record.required_scenario_ids)
 for trial_id in record.trial_result_ids:
  trial=_trial_results.get(trial_id)
  if trial is None or _trial_sessions.get(trial_id)!=sid:
   raise HTTPException(409,"The Release Record's trial evidence is no longer available in this sandbox session.")
  scenario_ids.add(trial.scenario_id)
  trial_evidence.append(asdict(trial))
 scenario_evidence=[]
 for scenario_id in sorted(scenario_ids):
  scenario=_scenarios.get(scenario_id)
  if scenario is None or _scenario_sessions.get(scenario_id)!=sid:
   raise HTTPException(409,"A required scenario definition is no longer available in this sandbox session.")
  scenario_evidence.append({**asdict(scenario),"scenario_config_hash":scenario.config_hash()})
 evidence={"format":"mubayyin-trial-evidence.v1","trials":trial_evidence,"scenarios":scenario_evidence,"scope":"Includes scenario definitions and trial results referenced by this Release Record at export time."}
 bundle=create_release_bundle(record.to_dict(),evidence=evidence)
 body=json.dumps(bundle,ensure_ascii=False,sort_keys=True,indent=2)
 return Response(content=body,media_type="application/json",headers={"Content-Disposition":f'attachment; filename="mubayyin-{record_id}.json"'})

@app.post("/releases/verify")
def verify_exported_release_bundle(bundle:dict):
 """Verify an exported bundle's content hash and, when configured, HMAC signature."""
 return verify_release_bundle(bundle)

@app.get("/releases/{baseline_record_id}/compare/{candidate_record_id}")
def compare_releases(baseline_record_id:str,candidate_record_id:str,request:Request):
 sid=_require_sandbox_session(request)
 records={rec.record_id:rec for history in _release_records.values() for rec in history}
 baseline=records.get(baseline_record_id);candidate=records.get(candidate_record_id)
 if not baseline or not candidate or _release_sessions.get(baseline_record_id)!=sid or _release_sessions.get(candidate_record_id)!=sid:raise HTTPException(404,"One or both sandbox Release Records were not found.")
 if baseline.system_id!=candidate.system_id:raise HTTPException(409,"Release Records must belong to the same system identity.")
 base_trials=set(baseline.trial_result_ids);candidate_trials=set(candidate.trial_result_ids)
 base_missing=set(baseline.missing_scenario_ids);candidate_missing=set(candidate.missing_scenario_ids)
 base_reasons=set(baseline.reason_codes);candidate_reasons=set(candidate.reason_codes)
 changed=baseline.system_config_hash!=candidate.system_config_hash
 return {
  "system_id":baseline.system_id,
  "baseline":{"record_id":baseline.record_id,"status":baseline.status.value,"system_config_hash":baseline.system_config_hash,"evidence_hash":baseline.evidence_hash,"scenario_set_version":baseline.scenario_set_version,"trial_result_ids":baseline.trial_result_ids,"required_scenario_ids":baseline.required_scenario_ids,"missing_scenario_ids":baseline.missing_scenario_ids,"reason_codes":baseline.reason_codes},
  "candidate":{"record_id":candidate.record_id,"status":candidate.status.value,"system_config_hash":candidate.system_config_hash,"evidence_hash":candidate.evidence_hash,"scenario_set_version":candidate.scenario_set_version,"trial_result_ids":candidate.trial_result_ids,"required_scenario_ids":candidate.required_scenario_ids,"missing_scenario_ids":candidate.missing_scenario_ids,"reason_codes":candidate.reason_codes},
  "comparison":{"configuration_changed":changed,"evidence_changed":baseline.evidence_hash!=candidate.evidence_hash,"release_status_changed":baseline.status!=candidate.status,"added_trial_result_ids":sorted(candidate_trials-base_trials),"removed_trial_result_ids":sorted(base_trials-candidate_trials),"newly_missing_scenario_ids":sorted(candidate_missing-base_missing),"coverage_gaps_resolved":sorted(base_missing-candidate_missing),"reason_codes_added":sorted(candidate_reasons-base_reasons),"reason_codes_removed":sorted(base_reasons-candidate_reasons),"interpretation":"Compare the evidence and conditions; a changed hash alone does not mean the candidate is safer. Review the underlying findings and human sign-off before using this comparison for a release decision."}
 }

@app.post("/releases")
def release(req:DecideReleaseRequest,request:Request):
 sid=_require_sandbox_session(request)
 s=_systems.get(req.system_id)
 if not s or _system_sessions.get(req.system_id)!=sid:raise HTTPException(404,"Sandbox system not found.")
 if len(req.result_ids)!=len(set(req.result_ids)):raise HTTPException(422,"Duplicate trial result IDs are not allowed.")
 if len(req.required_scenario_ids)!=len(set(req.required_scenario_ids)):raise HTTPException(422,"Duplicate required scenario IDs are not allowed.")
 unknown_scenarios=[x for x in req.required_scenario_ids if x not in _scenarios or _scenario_sessions.get(x)!=sid]
 if unknown_scenarios:raise HTTPException(404,"One or more required scenario IDs were not found.")
 unknown=[x for x in req.result_ids if x not in _trial_results]
 if unknown:raise HTTPException(404,"One or more trial result IDs were not found.")
 rs=[_trial_results[x] for x in req.result_ids]
 if not rs:raise HTTPException(400,"no valid trial results provided")
 for rid,r in zip(req.result_ids,rs):
  if _trial_sessions.get(rid)!=sid:raise HTTPException(404,"Sandbox trial result not found.")
  if _trial_system_ids.get(rid)!=req.system_id:raise HTTPException(409,"Trial evidence belongs to a different system.")
  sc=_scenarios.get(r.scenario_id)
  if not sc:raise HTTPException(409,"A referenced scenario is unavailable.")
  if r.system_config_hash!=s.config_hash():raise HTTPException(409,"Trial evidence is stale for the current system configuration; rerun the scenario.")
  if not r.scenario_config_hash or r.scenario_config_hash!=sc.config_hash():raise HTTPException(409,"Trial evidence is stale for the current scenario configuration; rerun the scenario.")
 h=_release_records.setdefault(req.system_id,[]);prev=h[-1].evidence_hash if h else None
 rec=decide_release(s,rs,ReleaseThresholds(max_critical_failures=req.max_critical_failures,max_major_failures=req.max_major_failures),req.approver,prev,req.scenario_set_version,req.required_scenario_ids)
 h.append(rec);_release_sessions[rec.record_id]=sid;p=rec.to_dict();p["persistence"]="memory_only";return p
