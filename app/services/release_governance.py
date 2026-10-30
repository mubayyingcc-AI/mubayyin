"""Enterprise release governance primitives for Mubayyin.

Deterministic, policy-driven functions only. This module does not execute
deployments, grant institutional authority, or certify regulatory compliance.
"""
from __future__ import annotations
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib, json
from typing import Any, Iterable

ENGINE_VERSION = "mubayyin-enterprise-release-governance.v1"
KNOWN_COMPONENTS = {"model", "prompt", "retrieval", "tool", "policy", "orchestration", "application", "configuration", "logging", "display", "documentation"}
ROUTINE_COMPONENTS = {"logging", "display", "documentation"}
MATERIAL_COMPONENTS = {"prompt", "retrieval", "application", "configuration"}
CONSEQUENTIAL_COMPONENTS = {"model", "tool", "policy", "orchestration"}

def canonical_hash(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()

def _system_components(system: Any) -> dict[str, str | None]:
    return {"model": f"{system.model_provider}:{system.model_version}", "prompt": system.prompt_version, "retrieval": system.retrieval_version, "tool": system.tool_version, "policy": system.policy_version}

@dataclass(frozen=True)
class SystemVersionSnapshot:
    schema_version: str
    system_id: str
    system_config_hash: str
    components: dict[str, str | None]
    predecessor_system_id: str | None
    predecessor_snapshot_hash: str | None
    change_manifest: tuple[dict[str, Any], ...]
    created_at: str
    snapshot_hash: str
    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["change_manifest"] = list(self.change_manifest)
        return value

def create_version_snapshot(system: Any, change_manifest: Iterable[dict[str, Any]] = (), predecessor_system_id: str | None = None, predecessor_snapshot_hash: str | None = None, created_at: str | None = None) -> SystemVersionSnapshot:
    manifest = tuple(sorted((dict(item) for item in change_manifest), key=lambda item: (str(item.get("component", "")), str(item.get("to_version", "")))))
    for item in manifest:
        component = str(item.get("component", "")).lower()
        if component not in KNOWN_COMPONENTS:
            raise ValueError(f"Unknown change component: {component or '(blank)'}")
        if not str(item.get("to_version", "")).strip():
            raise ValueError("Every change manifest entry requires to_version.")
        if "within_approved_boundary" not in item or not isinstance(item["within_approved_boundary"], bool):
            raise ValueError("Every change manifest entry requires boolean within_approved_boundary.")
    timestamp = created_at or datetime.now(timezone.utc).isoformat()
    payload = {"schema_version": "mubayyin.system-version-snapshot.v1", "system_id": system.system_id, "system_config_hash": system.config_hash(), "components": _system_components(system), "predecessor_system_id": predecessor_system_id, "predecessor_snapshot_hash": predecessor_snapshot_hash, "change_manifest": list(manifest), "created_at": timestamp}
    return SystemVersionSnapshot(**payload, snapshot_hash=canonical_hash(payload))

@dataclass(frozen=True)
class RiskAssessment:
    schema_version: str
    engine_version: str
    assessment_id: str
    system_id: str
    snapshot_hash: str
    policy_version: str
    risk_tier: str
    release_path: str
    reasons: tuple[str, ...]
    evidence_complete: bool
    mandatory_checks_passed: bool
    human_authorization_required: bool
    base_release_status: str
    effective_release_state: str
    assessed_at: str
    assessment_hash: str
    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["reasons"] = list(self.reasons)
        return value

def classify_change_manifest(manifest: Iterable[dict[str, Any]]) -> tuple[str, list[str]]:
    entries = list(manifest)
    if not entries:
        return "TIER_4_UNCERTAIN", ["NO_VERIFIABLE_CHANGE_MANIFEST"]
    reasons: list[str] = []
    tier = 1
    for item in entries:
        component = str(item.get("component", "")).lower()
        if component not in KNOWN_COMPONENTS:
            return "TIER_4_UNCERTAIN", ["UNKNOWN_CHANGE_COMPONENT"]
        if not item.get("within_approved_boundary", False):
            reasons.append("CHANGE_OUTSIDE_APPROVED_BOUNDARY")
            tier = max(tier, 4)
        if item.get("permission_expansion") or item.get("consequential"):
            reasons.append("CONSEQUENTIAL_OR_PERMISSION_EXPANDING_CHANGE")
            tier = max(tier, 3)
        if component in CONSEQUENTIAL_COMPONENTS:
            reasons.append("CONSEQUENTIAL_COMPONENT_CHANGED")
            tier = max(tier, 3)
        elif component in MATERIAL_COMPONENTS:
            reasons.append("MATERIAL_BEHAVIOUR_CHANGE")
            tier = max(tier, 2)
        elif component not in ROUTINE_COMPONENTS:
            reasons.append("CHANGE_REQUIRES_SCOPE_REVIEW")
            tier = max(tier, 2)
    if tier == 1:
        reasons.append("ROUTINE_CHANGE_WITHIN_APPROVED_BOUNDARY")
    elif tier == 2:
        reasons.append("MATERIAL_CHANGE_REQUIRES_ASSURANCE")
    elif tier == 3:
        reasons.append("CONSEQUENTIAL_CHANGE_REQUIRES_HUMAN_AUTHORIZATION")
    else:
        reasons.append("UNCERTAIN_CHANGE_MUST_BE_HELD")
    return f"TIER_{tier}", sorted(set(reasons))

def assess_release_path(*, system_id: str, snapshot_hash: str, manifest: Iterable[dict[str, Any]], base_release_status: str, critical_failures: int, major_failures: int, evidence_complete: bool, mandatory_checks_passed: bool, policy_version: str = "risk-policy.v1", human_authorization_required_by_policy: bool = False, assessed_at: str | None = None) -> RiskAssessment:
    tier, reasons = classify_change_manifest(manifest)
    release_path, effective = "HOLD_FOR_EVIDENCE", "HOLD_FOR_REPAIR"
    human_required = human_authorization_required_by_policy or tier in {"TIER_2", "TIER_3"}
    if not evidence_complete:
        reasons.append("REQUIRED_EVIDENCE_INCOMPLETE")
    elif not mandatory_checks_passed:
        reasons.append("MANDATORY_CHECKS_NOT_PASSED")
    elif critical_failures > 0 or base_release_status == "hold_for_repair":
        reasons.append("BASE_RELEASE_GATE_HOLD")
    elif tier == "TIER_4_UNCERTAIN":
        reasons.append("UNCERTAIN_CHANGE_CLASSIFICATION")
    elif tier == "TIER_3":
        human_required = True
        release_path, effective = "MANDATORY_HUMAN_AUTHORIZATION", "HOLD_FOR_AUTHORIZATION"
    elif tier == "TIER_2":
        human_required = True
        release_path, effective = "HUMAN_REVIEW_REQUIRED", "HOLD_FOR_REVIEW"
    elif major_failures > 0:
        human_required = True
        release_path, effective = "HUMAN_REVIEW_REQUIRED", "HOLD_FOR_REVIEW"
        reasons.append("MAJOR_FINDINGS_REQUIRE_REVIEW")
    elif human_required:
        release_path, effective = "HUMAN_REVIEW_REQUIRED", "HOLD_FOR_REVIEW"
    elif base_release_status == "safe_to_serve":
        release_path, effective = "AUTOMATED_FAST_TRACK_ELIGIBLE", "SAFE_TO_SERVE"
        reasons.append("ALL_FAST_TRACK_PRECONDITIONS_SATISFIED")
    else:
        release_path, effective = "HUMAN_REVIEW_REQUIRED", "HOLD_FOR_REVIEW"
    timestamp = assessed_at or datetime.now(timezone.utc).isoformat()
    body = {"schema_version": "mubayyin.risk-assessment.v1", "engine_version": ENGINE_VERSION, "system_id": system_id, "snapshot_hash": snapshot_hash, "policy_version": policy_version, "risk_tier": tier, "release_path": release_path, "reasons": sorted(set(reasons)), "evidence_complete": evidence_complete, "mandatory_checks_passed": mandatory_checks_passed, "human_authorization_required": human_required, "base_release_status": base_release_status, "effective_release_state": effective, "assessed_at": timestamp}
    digest = canonical_hash(body)
    return RiskAssessment(**body, assessment_id="rga_" + digest[:24], assessment_hash=digest)

def build_release_interoperability_payload(release_record: dict[str, Any], system_snapshot: dict[str, Any] | None, continuity: dict[str, Any], risk_assessment: dict[str, Any] | None) -> dict[str, Any]:
    return {"schema_version": "mubayyin.enterprise-release.v1", "producer": "Mubayyin Release Assurance", "release_record": release_record, "system_version_snapshot": system_snapshot, "release_continuity": continuity, "risk_assessment": risk_assessment, "limitations": ["This payload reports assessment evidence; it does not execute deployment.", "A hash verifies content integrity, not issuer identity or truth of submitted evidence.", "The release decision is not regulatory certification or institutional approval."]}
