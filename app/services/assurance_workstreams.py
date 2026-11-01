"""Research-grade primitives for Mubayyin's five phased R&D workstreams.

These functions are deterministic and dependency-free. They are not a semantic
Arabic evaluator, legal compliance engine, certification, or production scheduler.
All outputs carry explicit scope/limitations and are suitable for controlled
benchmarking until independently validated.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import hmac
import json
import re
import unicodedata
from typing import Any, Iterable

ENGINE_VERSION = "mubayyin-rd-assurance.v0.1"
SEVERITY_ORDER = {"none": 0, "minor": 1, "major": 2, "critical": 3}
RELEASE_ORDER = {"safe_to_serve": 0, "conditional_serve": 1, "hold_for_repair": 2}


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


# WP1 — Arabic-English financial evaluation ---------------------------------

_ARABIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")


def normalize_arabic_text(value: str) -> str:
    """Conservative text normalisation; preserves words and financial digits."""
    text = unicodedata.normalize("NFKC", value or "").translate(_ARABIC_DIGITS)
    text = re.sub(r"[\u064B-\u065F\u0670]", "", text)
    text = text.replace("ـ", "")
    text = re.sub(r"[إأآٱ]", "ا", text).replace("ى", "ي")
    text = re.sub(r"\s+", " ", text).strip().casefold()
    return text


def evaluate_bilingual_financial_output(
    output: str,
    *,
    required_terms: Iterable[str] = (),
    prohibited_terms: Iterable[str] = (),
    required_values: Iterable[str] = (),
    language_context: str = "unspecified",
) -> dict[str, Any]:
    """Run transparent phrase/value checks; no semantic quality is inferred."""
    observed = normalize_arabic_text(output)
    checks: list[dict[str, Any]] = []
    for term in required_terms:
        needle = normalize_arabic_text(str(term))
        checks.append({"rule": "required_term_present", "passed": bool(needle) and needle in observed, "reference": str(term)})
    for term in prohibited_terms:
        needle = normalize_arabic_text(str(term))
        checks.append({"rule": "prohibited_term_absent", "passed": not needle or needle not in observed, "reference": str(term)})
    for value in required_values:
        needle = normalize_arabic_text(str(value))
        checks.append({"rule": "required_financial_value_present", "passed": bool(needle) and needle in observed, "reference": str(value)})
    failed = [c for c in checks if not c["passed"]]
    return {
        "schema_version": "mubayyin.bilingual-checks.v1",
        "engine_version": ENGINE_VERSION,
        "language_context": language_context,
        "checks": checks,
        "passed": not failed,
        "failed_count": len(failed),
        "limitations": "Phrase and literal-value checks only. This does not assess meaning, dialect fluency, translation quality, hallucination, or financial correctness.",
    }


# WP2 — Evidence integrity ----------------------------------------------------

def create_evidence_manifest(
    evidence: dict[str, Any],
    *,
    system_snapshot_hash: str,
    scenario_set_version: str,
    evaluator_version: str = ENGINE_VERSION,
    policy_version: str,
    issuer: str,
    signing_key: str,
    created_at: str | None = None,
) -> dict[str, Any]:
    """Create an HMAC-attested manifest; the key is shared-secret authority."""
    if not signing_key:
        raise ValueError("A non-empty signing key is required.")
    if not all([system_snapshot_hash, scenario_set_version, evaluator_version, policy_version, issuer]):
        raise ValueError("Snapshot, scenario set, evaluator, policy and issuer are required.")
    payload = {
        "schema_version": "mubayyin.evidence-manifest.v1",
        "system_snapshot_hash": system_snapshot_hash,
        "scenario_set_version": scenario_set_version,
        "evaluator_version": evaluator_version,
        "policy_version": policy_version,
        "issuer": issuer,
        "created_at": created_at or datetime.now(timezone.utc).isoformat(),
        "evidence": evidence,
    }
    digest = hashlib.sha256(canonical_json(payload)).hexdigest()
    signature = hmac.new(signing_key.encode("utf-8"), digest.encode("ascii"), hashlib.sha256).hexdigest()
    return {**payload, "integrity": {"algorithm": "sha256", "digest": digest, "signature_algorithm": "hmac-sha256", "signature": signature}}


def verify_evidence_manifest(manifest: dict[str, Any], *, signing_key: str) -> dict[str, Any]:
    if not isinstance(manifest, dict) or manifest.get("schema_version") != "mubayyin.evidence-manifest.v1":
        return {"valid": False, "status": "unsupported_schema"}
    integrity = manifest.get("integrity")
    if not isinstance(integrity, dict) or integrity.get("algorithm") != "sha256" or integrity.get("signature_algorithm") != "hmac-sha256":
        return {"valid": False, "status": "malformed_integrity"}
    payload = {k: v for k, v in manifest.items() if k != "integrity"}
    try:
        digest = hashlib.sha256(canonical_json(payload)).hexdigest()
    except (TypeError, ValueError):
        return {"valid": False, "status": "malformed_payload"}
    digest_ok = hmac.compare_digest(digest, str(integrity.get("digest", "")))
    expected = hmac.new(signing_key.encode("utf-8"), digest.encode("ascii"), hashlib.sha256).hexdigest() if signing_key else ""
    signature_ok = bool(signing_key) and hmac.compare_digest(expected, str(integrity.get("signature", "")))
    return {
        "valid": digest_ok and signature_ok,
        "integrity_valid": digest_ok,
        "authenticity_verified": signature_ok,
        "status": "verified" if digest_ok and signature_ok else ("digest_mismatch" if not digest_ok else "signature_invalid_or_key_unavailable"),
        "limitations": "HMAC proves possession of a shared secret, not independent identity, truth of evidence, or public-key non-repudiation.",
    }


# WP3 — Behaviour change intelligence ---------------------------------------

def compare_behaviour_runs(baseline: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    """Compare scenario severity maps; unknown/missing scenarios are not treated as passes."""
    base = baseline.get("scenarios", {})
    cand = candidate.get("scenarios", {})
    if not isinstance(base, dict) or not isinstance(cand, dict):
        raise ValueError("Both runs must contain a scenarios mapping.")
    regressions, improvements, unchanged, missing = [], [], [], []
    for scenario_id, old in base.items():
        if scenario_id not in cand:
            missing.append(scenario_id)
            continue
        new = cand[scenario_id]
        old_rank = SEVERITY_ORDER.get(str(old).lower())
        new_rank = SEVERITY_ORDER.get(str(new).lower())
        if old_rank is None or new_rank is None:
            missing.append(scenario_id)
        elif new_rank > old_rank:
            regressions.append({"scenario_id": scenario_id, "from": old, "to": new})
        elif new_rank < old_rank:
            improvements.append({"scenario_id": scenario_id, "from": old, "to": new})
        else:
            unchanged.append(scenario_id)
    return {
        "schema_version": "mubayyin.behaviour-diff.v1",
        "baseline_id": baseline.get("run_id"),
        "candidate_id": candidate.get("run_id"),
        "regressions": regressions,
        "improvements": improvements,
        "unchanged": unchanged,
        "missing_or_unscorable": missing,
        "new_scenarios": sorted(set(cand) - set(base)),
        "regression_count": len(regressions),
        "limitations": "Compares supplied severity labels only; it does not infer causality, statistical significance, or detect untested behavioural changes.",
    }


# WP4 — Decision assurance ---------------------------------------------------

def decide_assurance(
    *,
    check_results: Iterable[dict[str, Any]],
    evidence_complete: bool,
    human_approval: bool = False,
    require_human_approval: bool = False,
    max_major_failures: int = 0,
    max_critical_failures: int = 0,
    regression_count: int = 0,
) -> dict[str, Any]:
    checks = list(check_results)
    failed = [c for c in checks if not c.get("passed", False)]
    critical = sum(1 for c in failed if str(c.get("severity", "major")).lower() == "critical")
    major = sum(1 for c in failed if str(c.get("severity", "major")).lower() == "major")
    reasons = []
    if not evidence_complete:
        reasons.append("EVIDENCE_INCOMPLETE")
    if critical > max_critical_failures:
        reasons.append("CRITICAL_FAILURE_THRESHOLD_EXCEEDED")
    if major > max_major_failures:
        reasons.append("MAJOR_FAILURE_THRESHOLD_EXCEEDED")
    if regression_count:
        reasons.append("BEHAVIOURAL_REGRESSION_DETECTED")
    if require_human_approval and not human_approval:
        reasons.append("HUMAN_APPROVAL_REQUIRED")
    if any(r in reasons for r in ("EVIDENCE_INCOMPLETE", "CRITICAL_FAILURE_THRESHOLD_EXCEEDED", "BEHAVIOURAL_REGRESSION_DETECTED")):
        status = "hold_for_repair"
    elif reasons:
        status = "conditional_serve"
    else:
        status = "safe_to_serve"
    return {
        "schema_version": "mubayyin.assurance-decision.v1",
        "status": status,
        "reasons": reasons,
        "counts": {"failed_checks": len(failed), "critical_failures": critical, "major_failures": major, "regressions": regression_count},
        "human_approval": {"required": require_human_approval, "present": human_approval},
        "decision_hash": sha256({"status": status, "reasons": reasons, "checks": checks, "evidence_complete": evidence_complete, "human_approval": human_approval}),
        "limitations": "Technical decision aid only. Institutional policy owners retain release authority; this is not certification or legal compliance advice.",
    }


# WP5 — Continuous assurance event contract ---------------------------------

def build_retest_event(
    *,
    tenant_ref: str,
    system_ref: str,
    previous_snapshot_hash: str,
    current_snapshot_hash: str,
    changed_components: Iterable[str],
    event_id: str | None = None,
) -> dict[str, Any]:
    components = sorted({str(c).strip().lower() for c in changed_components if str(c).strip()})
    if not tenant_ref or not system_ref or not current_snapshot_hash:
        raise ValueError("Tenant, system and current snapshot references are required.")
    material = bool(components) and any(c not in {"logging", "display", "documentation"} for c in components)
    changed = previous_snapshot_hash != current_snapshot_hash
    payload = {
        "schema_version": "mubayyin.retest-event.v1",
        "tenant_ref": tenant_ref,
        "system_ref": system_ref,
        "previous_snapshot_hash": previous_snapshot_hash or None,
        "current_snapshot_hash": current_snapshot_hash,
        "changed_components": components,
        "retest_required": changed and material,
        "reason": "MATERIAL_SYSTEM_CHANGE" if changed and material else ("NO_SNAPSHOT_CHANGE" if not changed else "NON_MATERIAL_CHANGE"),
    }
    payload["event_id"] = event_id or "evt_" + sha256(payload)[:24]
    payload["idempotency_key"] = sha256({"tenant_ref": tenant_ref, "system_ref": system_ref, "current_snapshot_hash": current_snapshot_hash, "components": components})
    return payload


# Integrated five-workstream assessment -------------------------------------

def run_five_workstream_assessment(
    *,
    output: str,
    required_terms: Iterable[str] = (),
    prohibited_terms: Iterable[str] = (),
    required_values: Iterable[str] = (),
    language_context: str = "ar-en",
    baseline_run: dict[str, Any] | None = None,
    candidate_run: dict[str, Any] | None = None,
    evidence_complete: bool = True,
    human_approval: bool = False,
    require_human_approval: bool = False,
    signing_key: str = "",
    system_snapshot_hash: str = "",
    scenario_set_version: str = "unversioned",
    policy_version: str = "unversioned",
    issuer: str = "customer-controlled-runner",
) -> dict[str, Any]:
    linguistic = evaluate_bilingual_financial_output(
        output, required_terms=required_terms, prohibited_terms=prohibited_terms,
        required_values=required_values, language_context=language_context,
    )
    diff = compare_behaviour_runs(baseline_run, candidate_run) if baseline_run is not None and candidate_run is not None else None
    regression_count = diff["regression_count"] if diff else 0
    decision_checks = [{"passed": c["passed"], "severity": "major", "rule": c["rule"]} for c in linguistic["checks"]]
    decision = decide_assurance(
        check_results=decision_checks, evidence_complete=evidence_complete,
        human_approval=human_approval, require_human_approval=require_human_approval,
        regression_count=regression_count,
    )
    evidence = {"linguistic": linguistic, "behaviour_diff": diff, "decision": decision}
    manifest = None
    if signing_key:
        manifest = create_evidence_manifest(
            evidence, system_snapshot_hash=system_snapshot_hash or "unbound",
            scenario_set_version=scenario_set_version, policy_version=policy_version,
            issuer=issuer, signing_key=signing_key,
        )
    return {
        "engine_version": ENGINE_VERSION,
        "workstreams": {
            "wp1_bilingual_financial_assurance": linguistic,
            "wp2_evidence_integrity": {"manifest": manifest, "signed": manifest is not None},
            "wp3_behaviour_change_intelligence": diff,
            "wp4_decision_assurance": decision,
            "wp5_continuous_assurance": {"event_contract": "build_retest_event", "integrated": False, "note": "Use build_retest_event with tenant-scoped snapshot references to create an idempotent retest trigger."},
        },
        "decision": decision,
        "limitations": "Research prototype. No model inference, dialect certification, persistent event queue, key management service, or automatic release action is performed.",
    }
