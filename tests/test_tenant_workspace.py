import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool

import app.api as api_module
from app.api import app


class DurableTenantWorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.originals = {
            "_db_engine": api_module._db_engine,
            "_database_ready": api_module._database_ready,
            "_database_error": api_module._database_error,
            "DATABASE_URL": api_module.DATABASE_URL,
            "PARTNER_ADMIN_TOKEN": api_module.PARTNER_ADMIN_TOKEN,
            "TENANT_ADMIN_TOKEN": api_module.TENANT_ADMIN_TOKEN,
        }
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        with self.engine.begin() as conn:
            conn.execute(text("""
                CREATE TABLE mubayyin_tenants (
                    tenant_id VARCHAR(80) PRIMARY KEY,
                    name VARCHAR(160) NOT NULL,
                    token_hash VARCHAR(64) UNIQUE NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    revoked_at DATETIME
                )
            """))
            conn.execute(text("""
                CREATE TABLE mubayyin_tenant_evidence_records (
                    tenant_id VARCHAR(80) NOT NULL,
                    record_type VARCHAR(24) NOT NULL,
                    record_id VARCHAR(80) NOT NULL,
                    system_id VARCHAR(80) NOT NULL,
                    payload TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (tenant_id, record_type, record_id)
                )
            """))
        api_module._db_engine = self.engine
        api_module._database_ready = True
        api_module._database_error = None
        api_module.DATABASE_URL = "sqlite://test"
        api_module.TENANT_ADMIN_TOKEN = "unit-test-admin-token"
        self.key_patch = patch.dict(os.environ, {"MUBAYYIN_ATTESTATION_KEY": ""})
        self.key_patch.start()
        self.addCleanup(self.key_patch.stop)
        self.client = TestClient(app, base_url="https://testserver")
        self.admin_headers = {"Authorization": "Bearer unit-test-admin-token"}

    def tearDown(self):
        self.engine.dispose()
        api_module._db_engine = self.originals["_db_engine"]
        api_module._database_ready = self.originals["_database_ready"]
        api_module._database_error = self.originals["_database_error"]
        api_module.DATABASE_URL = self.originals["DATABASE_URL"]
        api_module.PARTNER_ADMIN_TOKEN = self.originals["PARTNER_ADMIN_TOKEN"]
        api_module.TENANT_ADMIN_TOKEN = self.originals["TENANT_ADMIN_TOKEN"]

    def _provision(self, name):
        response = self.client.post(
            "/admin/tenants",
            headers=self.admin_headers,
            json={"name": name},
        )
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    def test_durable_release_survives_new_client_and_isolated_between_tenants(self):
        tenant = self._provision("Pilot Organisation A")
        other = self._provision("Pilot Organisation B")
        headers = {"Authorization": "Bearer " + tenant["api_key"]}
        other_headers = {"Authorization": "Bearer " + other["api_key"]}

        system = self.client.post("/tenant/systems", headers=headers, json={
            "system_id": "pilot-system-v1", "name": "Synthetic bank assistant",
            "organization": "Pilot Organisation A", "jurisdiction": "SA",
            "model_provider": "demo", "model_version": "v1",
            "prompt_version": "prompt-v1", "policy_version": "policy-v1"
        })
        self.assertEqual(system.status_code, 200, system.text)
        self.assertEqual(system.json()["persistence"], "durable")

        scenario = self.client.post("/tenant/scenarios", headers=headers, json={
            "scenario_id": "pilot-disclosure-1", "language": "en", "category": "disclosure",
            "risk_level": "medium", "user_input": "Synthetic customer asks about fees.",
            "expected_behavior": "Disclose the approved fee terms.",
            "required_disclosure": "Fees may apply."
        })
        self.assertEqual(scenario.status_code, 200, scenario.text)

        trial = self.client.post("/tenant/trials", headers=headers, json={
            "system_id": "pilot-system-v1", "scenario_id": "pilot-disclosure-1",
            "model_output": "Fees may apply. Here are the approved terms."
        })
        self.assertEqual(trial.status_code, 200, trial.text)
        self.assertEqual(trial.json()["persistence"], "durable")

        release = self.client.post("/tenant/releases", headers=headers, json={
            "system_id": "pilot-system-v1", "result_ids": [trial.json()["result_id"]],
            "required_scenario_ids": ["pilot-disclosure-1"],
            "scenario_set_version": "pilot-sa-v1", "approver": "Named pilot reviewer"
        })
        self.assertEqual(release.status_code, 200, release.text)
        record_id = release.json()["record_id"]
        self.assertEqual(release.json()["persistence"], "durable")
        late_review = self.client.post(f"/tenant/trials/{trial.json()['result_id']}/review", headers=headers, json={
            "reviewer": "Late reviewer", "agrees_with_automation": False, "comment": "Attempted post-release edit"
        })
        self.assertEqual(late_review.status_code, 409)

        # The tenant API reads from PostgreSQL-backed storage, not the public sandbox's RAM maps.
        second_client = TestClient(app, base_url="https://testserver")
        restored = second_client.get(f"/tenant/releases/{record_id}", headers=headers)
        self.assertEqual(restored.status_code, 200, restored.text)
        self.assertEqual(restored.json()["record_id"], record_id)
        self.assertEqual(restored.json()["persistence"], "durable")

        exported = second_client.get(f"/tenant/releases/{record_id}/export", headers=headers)
        self.assertEqual(exported.status_code, 200, exported.text)
        bundle = exported.json()
        self.assertEqual(bundle["evidence"]["trials"][0]["result_id"], trial.json()["result_id"])
        verified = second_client.post("/releases/verify", json=bundle)
        self.assertEqual(verified.status_code, 200)
        self.assertTrue(verified.json()["integrity_valid"])

        cross_tenant = second_client.get(f"/tenant/releases/{record_id}", headers=other_headers)
        self.assertEqual(cross_tenant.status_code, 404)

    def test_admin_authentication_and_tenant_key_rotation(self):
        denied = self.client.post("/admin/tenants", json={"name": "No Auth"})
        self.assertEqual(denied.status_code, 401)
        tenant = self._provision("Rotation Test")
        old_headers = {"Authorization": "Bearer " + tenant["api_key"]}
        rotated = self.client.post(
            f'/admin/tenants/{tenant["tenant_id"]}/rotate-key',
            headers=self.admin_headers,
        )
        self.assertEqual(rotated.status_code, 200, rotated.text)
        self.assertEqual(self.client.get("/tenant/me", headers=old_headers).status_code, 401)
        new_headers = {"Authorization": "Bearer " + rotated.json()["api_key"]}
        me = self.client.get("/tenant/me", headers=new_headers)
        self.assertEqual(me.status_code, 200, me.text)
        self.assertEqual(me.json()["tenant_id"], tenant["tenant_id"])
        revoked = self.client.post(
            f'/admin/tenants/{tenant["tenant_id"]}/revoke',
            headers=self.admin_headers,
        )
        self.assertEqual(revoked.status_code, 200, revoked.text)
        self.assertEqual(self.client.get("/tenant/me", headers=new_headers).status_code, 401)

    def test_tenant_evidence_endpoints_fail_closed_without_database(self):
        api_module._database_ready = False
        response = self.client.get("/tenant/me", headers={"Authorization": "Bearer " + "x" * 54})
        self.assertEqual(response.status_code, 503)


if __name__ == "__main__":
    unittest.main()
