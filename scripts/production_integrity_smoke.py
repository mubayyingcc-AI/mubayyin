#!/usr/bin/env python3
"""Safe production smoke test for Mubayyin tenant PostgreSQL evidence.

This script creates only uniquely named synthetic test tenants and evidence.
It never reads, changes, or deletes existing tenant records.

Two-phase procedure:
  1. create: provision isolated test tenants and build a two-version evidence chain.
  2. verify: after an application restart/redeploy, re-read and verify the same chain.

Secrets are read from environment variables and stored only in a private state
file under the user's home directory. Never commit or share that state file.
"""
from __future__ import annotations

import argparse
import json
import os
import secrets
import stat
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE_URL = os.getenv(
    "MUBAYYIN_BASE_URL",
    "https://mubayyin-web-production.up.railway.app",
).rstrip("/")
STATE_FILE = Path.home() / ".mubayyin-production-smoke-state.json"
TIMEOUT = 25


class SmokeError(RuntimeError):
    pass


def request(method: str, path: str, *, token: str | None = None, body: dict | None = None):
    headers = {"Accept": "application/json"}
    data = None
    if token:
        headers["Authorization"] = "Bearer " + token
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(BASE_URL + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as response:
            raw = response.read()
            return response.status, json.loads(raw.decode("utf-8")) if raw else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            detail = json.loads(raw)
        except json.JSONDecodeError:
            detail = raw[:500]
        raise SmokeError(f"{method} {path} returned HTTP {exc.code}: {detail}") from None
    except (urllib.error.URLError, TimeoutError) as exc:
        raise SmokeError(f"Could not reach {BASE_URL}{path}: {exc}") from None


def require(condition: bool, message: str):
    if not condition:
        raise SmokeError(message)


def check_health():
    status, health = request("GET", "/health")
    require(status == 200 and health.get("status") == "ok", "Health endpoint did not return status=ok.")
    status, ready = request("GET", "/ready")
    require(status == 200 and ready.get("ready") is True, "Readiness endpoint did not return ready=true.")
    require(ready.get("database") == "ready", "Production readiness does not confirm PostgreSQL; refusing to continue.")
    print("PASS: application health and PostgreSQL readiness")


def post(path: str, token: str, body: dict, expected_status: int = 200):
    status, data = request("POST", path, token=token, body=body)
    require(status == expected_status, f"Unexpected HTTP status {status} for {path}.")
    return data


def create_tenant(admin_token: str, name: str):
    result = post("/admin/tenants", admin_token, {"name": name}, 201)
    require(result.get("api_key") and result.get("tenant_id"), "Tenant provisioning response omitted credentials or ID.")
    return {"tenant_id": result["tenant_id"], "api_key": result["api_key"]}


def create_system(token: str, system_id: str, model_version: str, prompt_version: str):
    return post("/tenant/systems", token, {
        "system_id": system_id,
        "name": "Synthetic production integrity test system",
        "organization": "Mubayyin internal verification",
        "jurisdiction": "SA",
        "model_provider": "customer-controlled",
        "model_version": model_version,
        "prompt_version": prompt_version,
        "retrieval_version": "synthetic-kb-v1",
        "tool_version": "synthetic-tools-v1",
        "policy_version": "synthetic-policy-v1",
    })


def create_release(token: str, system_id: str, scenario_id: str, predecessor_record_id: str | None = None):
    post("/tenant/scenarios", token, {
        "scenario_id": scenario_id,
        "language": "en",
        "category": "financial_disclosure",
        "risk_level": "low",
        "user_input": "What fees may apply?",
        "expected_behavior": "Fees may apply.",
        "required_disclosure": "Fees may apply.",
        "source": "synthetic",
    })
    trial = post("/tenant/trials", token, {
        "system_id": system_id,
        "scenario_id": scenario_id,
        "model_output": "Fees may apply.",
    })
    require(trial.get("deterministic_checks") and all(x.get("passed") for x in trial["deterministic_checks"]),
            "Synthetic trial did not pass its configured deterministic checks.")
    require(trial.get("final_severity") == "none", "Synthetic trial did not produce the expected clean result.")
    body = {
        "system_id": system_id,
        "result_ids": [trial["result_id"]],
        "required_scenario_ids": [scenario_id],
        "scenario_set_version": "production-smoke-v1",
        "approver": "Mubayyin controlled production smoke test",
    }
    if predecessor_record_id:
        body["predecessor_record_id"] = predecessor_record_id
    release = post("/tenant/releases", token, body)
    require(release.get("record_id") and release.get("evidence_hash"), "Release Record response omitted identity or evidence hash.")
    return release


def create_snapshot(token: str, system_id: str, component: str, old: str, new: str,
                    predecessor_snapshot_id: str | None = None):
    body = {"change_manifest": [{
        "component": component,
        "from_version": old,
        "to_version": new,
        "within_approved_boundary": True,
    }]}
    if predecessor_snapshot_id:
        body["predecessor_snapshot_id"] = predecessor_snapshot_id
    return post(f"/tenant/systems/{system_id}/version-snapshots", token, body, 201)


def create():
    admin = os.getenv("MUBAYYIN_TENANT_ADMIN_TOKEN", "").strip()
    require(len(admin) >= 32, "Set MUBAYYIN_TENANT_ADMIN_TOKEN in this terminal; do not paste it into chat.")
    check_health()
    suffix = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "_" + secrets.token_hex(3)
    owner = create_tenant(admin, "Mubayyin production integrity owner " + suffix)
    other = create_tenant(admin, "Mubayyin production isolation control " + suffix)
    owner_token, other_token = owner["api_key"], other["api_key"]
    owner_identity = request("GET", "/tenant/me", token=owner_token)[1]
    require(owner_identity.get("tenant_id") == owner["tenant_id"], "New owner tenant identity did not read back.")

    s1, s2 = "smoke-v1-" + suffix, "smoke-v2-" + suffix
    create_system(owner_token, s1, "synthetic-model-v1", "synthetic-prompt-v1")
    r1 = create_release(owner_token, s1, "smoke-scenario-v1-" + suffix)
    snap1 = create_snapshot(owner_token, s1, "logging", "1", "2")
    risk1 = post(f"/tenant/releases/{r1['record_id']}/risk-assessment", owner_token,
                 {"snapshot_id": snap1["snapshot_id"]}, 201)

    create_system(owner_token, s2, "synthetic-model-v2", "synthetic-prompt-v2")
    r2 = create_release(owner_token, s2, "smoke-scenario-v2-" + suffix, r1["record_id"])
    snap2 = create_snapshot(owner_token, s2, "model", "synthetic-model-v1", "synthetic-model-v2",
                             snap1["snapshot_id"])
    risk2 = post(f"/tenant/releases/{r2['record_id']}/risk-assessment", owner_token,
                 {"snapshot_id": snap2["snapshot_id"]}, 201)

    require(snap2.get("predecessor_snapshot_hash") == snap1.get("snapshot_hash"),
            "New snapshot did not link to its predecessor fingerprint.")
    require(r2.get("previous_record_hash") == r1.get("evidence_hash"),
            "New Release Record did not link to its predecessor evidence hash.")
    require(risk2.get("risk_tier") == "TIER_3" and
            risk2.get("release_path") == "MANDATORY_HUMAN_AUTHORIZATION",
            "Material model change did not require mandatory human authorization.")

    state = {
        "base_url": BASE_URL,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "owner": owner,
        "other": other,
        "system_v1": s1,
        "system_v2": s2,
        "release_v1_id": r1["record_id"],
        "release_v1_hash": r1["evidence_hash"],
        "release_v2_id": r2["record_id"],
        "release_v2_previous_hash": r2["previous_record_hash"],
        "snapshot_v1_id": snap1["snapshot_id"],
        "snapshot_v1_hash": snap1["snapshot_hash"],
        "snapshot_v2_id": snap2["snapshot_id"],
        "snapshot_v2_hash": snap2["snapshot_hash"],
        "risk_v1_id": r1["record_id"],
        "risk_v2_id": r2["record_id"],
    }
    temp = STATE_FILE.with_suffix(".tmp")
    temp.write_text(json.dumps(state, indent=2), encoding="utf-8")
    try:
        os.chmod(temp, stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        pass
    temp.replace(STATE_FILE)
    try:
        os.chmod(STATE_FILE, stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        pass
    print("PASS: two synthetic tenants provisioned; API keys stored locally, not displayed.")
    print("PASS: two system versions, two Release Records, two snapshots and two risk assessments created.")
    print("PASS: version 2 links to version 1 by snapshot hash and Release Record evidence hash.")
    print("PASS: model change requires mandatory human authorization; this script does not authorize deployment.")
    print(f"Private verification state saved to: {STATE_FILE}")
    verify()


def verify():
    require(STATE_FILE.exists(), f"No state file found at {STATE_FILE}; run --create first.")
    require(BASE_URL == json.loads(STATE_FILE.read_text(encoding="utf-8")).get("base_url"),
            "MUBAYYIN_BASE_URL differs from the URL used to create the test evidence.")
    state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    owner, other = state["owner"], state["other"]
    token, other_token = owner["api_key"], other["api_key"]
    check_health()

    identity = request("GET", "/tenant/me", token=token)[1]
    require(identity.get("tenant_id") == owner["tenant_id"] and
            identity.get("evidence_storage") == "durable_postgresql",
            "Tenant identity did not confirm durable PostgreSQL storage.")

    continuity = request("GET", f"/tenant/releases/{state['release_v2_id']}/continuity", token=token)[1]
    records = continuity.get("release_records", [])
    snapshots = continuity.get("version_chain", [])
    require(continuity.get("continuity_count") == 2 and len(records) == 2,
            "Expected exactly two connected Release Records.")
    require([x.get("record_id") for x in records] ==
            [state["release_v1_id"], state["release_v2_id"]],
            "Release Record history does not match the saved test chain.")
    require([x.get("snapshot_hash") for x in snapshots] ==
            [state["snapshot_v1_hash"], state["snapshot_v2_hash"]],
            "Version snapshot history does not match the saved test chain.")
    require(records[1].get("previous_record_hash") == records[0].get("evidence_hash"),
            "Release Record predecessor hash does not verify.")
    require(snapshots[1].get("predecessor_snapshot_hash") == snapshots[0].get("snapshot_hash"),
            "Version snapshot predecessor hash does not verify.")

    risk2 = request("GET", f"/tenant/releases/{state['release_v2_id']}/risk-assessment", token=token)[1]
    require(risk2.get("snapshot_id") == state["snapshot_v2_id"] and
            risk2.get("release_path") == "MANDATORY_HUMAN_AUTHORIZATION",
            "Version 2 risk assessment did not survive or is not bound to the exact snapshot.")

    status, denied = request("GET", f"/tenant/releases/{state['release_v2_id']}/continuity", token=other_token) if False else (None, None)
    # The control tenant must not be able to read the owner's evidence. A 404 is expected.
    try:
        request("GET", f"/tenant/releases/{state['release_v2_id']}/continuity", token=other_token)
    except SmokeError as exc:
        require("HTTP 404" in str(exc), "Cross-tenant isolation returned an unexpected error: " + str(exc))
    else:
        raise SmokeError("Cross-tenant isolation failure: second tenant read the owner's Release Record.")
    try:
        request("GET", f"/tenant/systems/{state['system_v2']}/version-snapshots", token=other_token)
    except SmokeError as exc:
        require("HTTP 404" in str(exc), "Cross-tenant snapshot isolation returned an unexpected error: " + str(exc))
    else:
        raise SmokeError("Cross-tenant isolation failure: second tenant read the owner's snapshots.")

    print("PASS: application reports PostgreSQL ready.")
    print("PASS: tenant identity and evidence are readable.")
    print("PASS: both Release Records and both version snapshots remain connected.")
    print("PASS: exact risk assessment remains bound to version 2.")
    print("PASS: second tenant receives 404 for owner's release and snapshot evidence.")
    print("PASS: production persistence and tenant isolation checks completed.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("create", "verify"),
                        help="create synthetic production evidence, or verify existing evidence after a restart")
    args = parser.parse_args()
    try:
        if args.mode == "create":
            create()
        else:
            verify()
    except SmokeError as exc:
        print("FAIL:", exc, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
