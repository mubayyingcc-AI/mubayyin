"""Opt-in PostgreSQL integration test for durable tenant evidence and cross-version lineage.

Run only against a disposable CI/test database using MUBAYYIN_TEST_DATABASE_URL.
Never point this test at production data.
"""
import os
import unittest
from sqlalchemy import create_engine, text
from fastapi.testclient import TestClient

TEST_DATABASE_URL = os.getenv("MUBAYYIN_TEST_DATABASE_URL")


@unittest.skipUnless(TEST_DATABASE_URL, "requires isolated MUBAYYIN_TEST_DATABASE_URL")
class PostgreSQLReleaseContinuityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import app.api as api
        cls.api = api
        cls.original = {
            "DATABASE_URL": api.DATABASE_URL,
            "TENANT_ADMIN_TOKEN": api.TENANT_ADMIN_TOKEN,
            "PARTNER_ADMIN_TOKEN": api.PARTNER_ADMIN_TOKEN,
            "_db_engine": api._db_engine,
            "_database_ready": api._database_ready,
            "_database_error": api._database_error,
        }
        api.DATABASE_URL = TEST_DATABASE_URL
        api.TENANT_ADMIN_TOKEN = "postgres-integration-admin-token"
        api._db_engine = None
        api._database_ready = False
        api._database_error = None
        api._initialize_storage()
        if not api._database_ready:
            raise RuntimeError("PostgreSQL test database initialization failed")
        # This database is dedicated to this CI job. Do not use a shared or production DB.
        with api._db_engine.begin() as conn:
            conn.execute(text("TRUNCATE mubayyin_tenant_evidence_records, mubayyin_tenants RESTART IDENTITY CASCADE"))
        cls.client = TestClient(api.app)

    @classmethod
    def tearDownClass(cls):
        cls.client.close()
        if cls.api._db_engine:
            cls.api._db_engine.dispose()
        for key, value in cls.original.items():
            setattr(cls.api, key, value)

    def _tenant(self, name):
        response = self.client.post(
            "/admin/tenants",
            headers={"Authorization": "Bearer postgres-integration-admin-token"},
            json={"name": name},
        )
        self.assertEqual(response.status_code, 201, response.text)
        payload = response.json()
        return {"Authorization": "Bearer " + payload["api_key"]}

    def _system(self, headers, system_id, model_version, prompt_version):
        response = self.client.post("/tenant/systems", headers=headers, json={
            "system_id": system_id, "name": "Synthetic bank assistant",
            "organization": "Integration Test", "jurisdiction": "SA",
            "model_provider": "customer", "model_version": model_version,
            "prompt_version": prompt_version, "retrieval_version": "kb-1",
            "tool_version": "tools-1", "policy_version": "policy-1",
        })
        self.assertEqual(response.status_code, 200, response.text)

    def _release(self, headers, system_id, scenario_id, predecessor=None):
        scenario = self.client.post("/tenant/scenarios", headers=headers, json={
            "scenario_id": scenario_id, "language": "en", "category": "disclosure",
            "risk_level": "low", "user_input": "Ask about fees",
            "expected_behavior": "Disclose fees", "required_disclosure": "Fees may apply",
        })
        self.assertEqual(scenario.status_code, 200, scenario.text)
        trial = self.client.post("/tenant/trials", headers=headers, json={
            "system_id": system_id, "scenario_id": scenario_id,
            "model_output": "Fees may apply.",
        })
        self.assertEqual(trial.status_code, 200, trial.text)
        body = {
            "system_id": system_id, "result_ids": [trial.json()["result_id"]],
            "required_scenario_ids": [scenario_id], "scenario_set_version": "sa-v1",
        }
        if predecessor:
            body["predecessor_record_id"] = predecessor
        release = self.client.post("/tenant/releases", headers=headers, json=body)
        self.assertEqual(release.status_code, 200, release.text)
        return release.json()

    def test_postgres_restart_tenant_isolation_and_two_version_release_chain(self):
        owner = self._tenant("Postgres lineage owner")
        other = self._tenant("Postgres lineage isolation tenant")

        self._system(owner, "bank-v1", "model-1", "prompt-1")
        release1 = self._release(owner, "bank-v1", "disclosure-v1")
        snapshot1_response = self.client.post(
            "/tenant/systems/bank-v1/version-snapshots", headers=owner,
            json={"change_manifest": [{
                "component": "logging", "from_version": "1", "to_version": "2",
                "within_approved_boundary": True,
            }]},
        )
        self.assertEqual(snapshot1_response.status_code, 201, snapshot1_response.text)
        snapshot1 = snapshot1_response.json()
        risk1 = self.client.post(
            f"/tenant/releases/{release1['record_id']}/risk-assessment",
            headers=owner, json={"snapshot_id": snapshot1["snapshot_id"]},
        )
        self.assertEqual(risk1.status_code, 201, risk1.text)

        self._system(owner, "bank-v2", "model-2", "prompt-2")
        release2 = self._release(owner, "bank-v2", "disclosure-v2", release1["record_id"])
        snapshot2_response = self.client.post(
            "/tenant/systems/bank-v2/version-snapshots", headers=owner,
            json={"predecessor_snapshot_id": snapshot1["snapshot_id"],
                  "change_manifest": [{
                      "component": "model", "from_version": "model-1",
                      "to_version": "model-2", "within_approved_boundary": True,
                  }]},
        )
        self.assertEqual(snapshot2_response.status_code, 201, snapshot2_response.text)
        snapshot2 = snapshot2_response.json()
        self.assertEqual(snapshot2["predecessor_snapshot_hash"], snapshot1["snapshot_hash"])
        risk2 = self.client.post(
            f"/tenant/releases/{release2['record_id']}/risk-assessment",
            headers=owner, json={"snapshot_id": snapshot2["snapshot_id"]},
        )
        self.assertEqual(risk2.status_code, 201, risk2.text)
        self.assertEqual(risk2.json()["release_path"], "MANDATORY_HUMAN_AUTHORIZATION")

        # Recreate the SQLAlchemy engine to simulate process restart; data must remain in PostgreSQL.
        self.api._db_engine.dispose()
        self.api._db_engine = None
        self.api._database_ready = False
        self.api._initialize_storage()
        self.assertTrue(self.api._database_ready, self.api._database_error)

        continuity = self.client.get(
            f"/tenant/releases/{release2['record_id']}/continuity", headers=owner,
        )
        self.assertEqual(continuity.status_code, 200, continuity.text)
        data = continuity.json()
        self.assertEqual([x["snapshot_hash"] for x in data["version_chain"]],
                         [snapshot1["snapshot_hash"], snapshot2["snapshot_hash"]])
        self.assertEqual({x["record_id"] for x in data["release_records"]},
                         {release1["record_id"], release2["record_id"]})
        self.assertEqual(release2["previous_record_hash"], release1["evidence_hash"])

        # Tenant isolation must hold after the engine has been recreated.
        denied = self.client.get(
            f"/tenant/releases/{release2['record_id']}/continuity", headers=other,
        )
        self.assertEqual(denied.status_code, 404)
        snapshot_denied = self.client.get(
            "/tenant/systems/bank-v2/version-snapshots", headers=other,
        )
        self.assertEqual(snapshot_denied.status_code, 404)


if __name__ == "__main__":
    unittest.main()
