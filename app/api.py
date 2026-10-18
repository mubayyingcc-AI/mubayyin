"""Mubayyin HTTP API — verified core engine and public GCC test lab."""
from __future__ import annotations
from pathlib import Path
import secrets, json, os, re
from dataclasses import asdict
from enum import Enum
from typing import Optional
from fastapi import FastAPI, HTTPException, Header, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from app.models.core import AISystem, ScenarioCase, HumanReview, Severity, DeterministicCheckResult, JudgeScore, TrialResult, ReleaseRecord, ReleaseStatus
from app.services.evaluator import run_trial
from app.services.release_gate import decide_release, ReleaseThresholds
app=FastAPI(title="Mubayyin Release Assurance API",description="Vendor-neutral AI release-assurance engine — GCC beachhead.",version="0.2.0")
_systems={};_scenarios={};_release_records={};_trial_results={}
class CreateSystemRequest(BaseModel):
 system_id:str;name:str;organization:str;jurisdiction:str;model_provider:str;model_version:str;prompt_version:str;retrieval_version:Optional[str]=None;policy_version:str="v1";tool_version:Optional[str]=None
class CreateScenarioRequest(BaseModel):
 scenario_id:str;language:str;dialect:Optional[str]=None;category:str;risk_level:str;user_input:str;expected_behavior:str;forbidden_behavior:Optional[str]=None;requires_escalation:bool=False;required_disclosure:Optional[str]=None;source:str="synthetic"
class RunTrialRequest(BaseModel): system_id:str;scenario_id:str;model_output:str
class HumanReviewRequest(BaseModel): reviewer:str;agrees_with_automation:bool;override_severity:Optional[str]=None;comment:str=""
class DecideReleaseRequest(BaseModel): system_id:str;result_ids:list[str];approver:Optional[str]=None;max_critical_failures:int=0;max_major_failures:int=3;scenario_set_version:str="v1"
DATABASE_URL=os.getenv("DATABASE_URL","");PARTNER_ADMIN_TOKEN=os.getenv("PARTNER_ADMIN_TOKEN","");_db_engine=None;_database_ready=False;_database_error=None
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
def startup():_initialize_storage()
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
def website():return FileResponse(Path(__file__).parent/"static"/"index.html",media_type="text/html")
@app.get("/ar",include_in_schema=False)
def arabic():return FileResponse(Path(__file__).parent/"static"/"arabic.html",media_type="text/html")
@app.post("/systems")
def system(req:CreateSystemRequest):
 s=AISystem(**req.dict());d=_persist("system",s.system_id,s.system_id,s);_systems[s.system_id]=s;return {"system_id":s.system_id,"config_hash":s.config_hash(),"persistence":"durable" if d else "memory_only"}
@app.post("/scenarios")
def scenario(req:CreateScenarioRequest):
 s=ScenarioCase(**req.dict());d=_persist("scenario",s.scenario_id,"scenario:"+s.scenario_id,s);_scenarios[s.scenario_id]=s;return {"scenario_id":s.scenario_id,"persistence":"durable" if d else "memory_only"}
@app.post("/trials")
def trial(req:RunTrialRequest):
 s=_systems.get(req.system_id);sc=_scenarios.get(req.scenario_id)
 if not s or not sc:raise HTTPException(404,"system or scenario not found")
 r=run_trial(sc,req.model_output);r.system_config_hash=s.config_hash();d=_persist("trial",r.result_id,s.system_id,r);_trial_results[r.result_id]=r
 return {"result_id":r.result_id,"final_severity":r.final_severity.value,"is_failure":r.is_failure(),"deterministic_checks":[c.__dict__ for c in r.deterministic_checks],"judge_scores":[{"judge_name":j.judge_name,"groundedness":j.groundedness,"policy_adherence":j.policy_adherence,"language_quality":j.language_quality,"escalation_quality":j.escalation_quality,"privacy_behavior":j.privacy_behavior,"severity":j.severity.value,"reason":j.reason} for j in r.judge_scores],"system_config_hash":r.system_config_hash,"persistence":"durable" if d else "memory_only"}
@app.post("/releases")
def release(req:DecideReleaseRequest):
 s=_systems.get(req.system_id)
 if not s:raise HTTPException(404,"system not found")
 rs=[_trial_results[x] for x in req.result_ids if x in _trial_results]
 if not rs:raise HTTPException(400,"no valid trial results provided")
 h=_release_records.setdefault(req.system_id,[]);prev=h[-1].evidence_hash if h else None
 rec=decide_release(s,rs,ReleaseThresholds(max_critical_failures=req.max_critical_failures,max_major_failures=req.max_major_failures),req.approver,prev,req.scenario_set_version);d=_persist("release",rec.record_id,s.system_id,rec,immutable=True);h.append(rec);p=rec.to_dict();p["persistence"]="durable" if d else "memory_only";return p
