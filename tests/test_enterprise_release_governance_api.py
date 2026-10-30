import os
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool
import app.api as api
from app.api import app

class EnterpriseReleaseGovernanceAPITests(unittest.TestCase):
    def setUp(self):
        self.engine=create_engine("sqlite://",connect_args={"check_same_thread":False},poolclass=StaticPool)
        with self.engine.begin() as c:
            c.execute(text("CREATE TABLE mubayyin_tenants (tenant_id VARCHAR(80) PRIMARY KEY,name VARCHAR(160) NOT NULL,token_hash VARCHAR(64) UNIQUE NOT NULL,created_at DATETIME DEFAULT CURRENT_TIMESTAMP,revoked_at DATETIME)"))
            c.execute(text("CREATE TABLE mubayyin_tenant_evidence_records (tenant_id VARCHAR(80) NOT NULL,record_type VARCHAR(24) NOT NULL,record_id VARCHAR(80) NOT NULL,system_id VARCHAR(80) NOT NULL,payload TEXT NOT NULL,created_at DATETIME DEFAULT CURRENT_TIMESTAMP,PRIMARY KEY(tenant_id,record_type,record_id))"))
        self.old={k:getattr(api,k) for k in ("_db_engine","_database_ready","DATABASE_URL","TENANT_ADMIN_TOKEN")}
        api._db_engine=self.engine;api._database_ready=True;api.DATABASE_URL="sqlite://test";api.TENANT_ADMIN_TOKEN="test-admin"
        self.patch=patch.dict(os.environ,{"MUBAYYIN_ATTESTATION_KEY":""});self.patch.start()
        self.client=TestClient(app,base_url="https://testserver")
        tenant=self.client.post("/admin/tenants",headers={"Authorization":"Bearer test-admin"},json={"name":"Governance test tenant"})
        self.assertEqual(tenant.status_code,201,tenant.text)
        self.headers={"Authorization":"Bearer "+tenant.json()["api_key"]}
        other=self.client.post("/admin/tenants",headers={"Authorization":"Bearer test-admin"},json={"name":"Other tenant"})
        self.other_headers={"Authorization":"Bearer "+other.json()["api_key"]}
    def tearDown(self):
        self.patch.stop()
        for k,v in self.old.items():setattr(api,k,v)
        self.engine.dispose()
    def test_snapshot_risk_and_interoperability_are_tenant_scoped(self):
        system=self.client.post("/tenant/systems",headers=self.headers,json={"system_id":"bank-v1","name":"Synthetic bank assistant","organization":"Test","jurisdiction":"SA","model_provider":"customer","model_version":"m1","prompt_version":"p1","retrieval_version":"r1","tool_version":"t1","policy_version":"pol1"})
        self.assertEqual(system.status_code,200,system.text)
        scenario=self.client.post("/tenant/scenarios",headers=self.headers,json={"scenario_id":"disclosure-1","language":"en","category":"disclosure","risk_level":"low","user_input":"Ask about fees","expected_behavior":"Disclose fees","required_disclosure":"Fees may apply"})
        self.assertEqual(scenario.status_code,200,scenario.text)
        trial=self.client.post("/tenant/trials",headers=self.headers,json={"system_id":"bank-v1","scenario_id":"disclosure-1","model_output":"Fees may apply."})
        self.assertEqual(trial.status_code,200,trial.text)
        release=self.client.post("/tenant/releases",headers=self.headers,json={"system_id":"bank-v1","result_ids":[trial.json()["result_id"]],"required_scenario_ids":["disclosure-1"],"scenario_set_version":"sa-v1"})
        self.assertEqual(release.status_code,200,release.text)
        snapshot=self.client.post("/tenant/systems/bank-v1/version-snapshots",headers=self.headers,json={"change_manifest":[{"component":"logging","from_version":"1","to_version":"2","within_approved_boundary":True}]})
        self.assertEqual(snapshot.status_code,201,snapshot.text)
        risk=self.client.post(f"/tenant/releases/{release.json()['record_id']}/risk-assessment",headers=self.headers,json={"snapshot_id":snapshot.json()["snapshot_id"]})
        self.assertEqual(risk.status_code,201,risk.text)
        self.assertEqual(risk.json()["release_path"],"AUTOMATED_FAST_TRACK_ELIGIBLE")
        exported=self.client.get(f"/tenant/integrations/releases/{release.json()['record_id']}",headers=self.headers)
        self.assertEqual(exported.status_code,200,exported.text)
        self.assertEqual(exported.json()["schema_version"],"mubayyin.enterprise-release.v1")
        denied=self.client.get(f"/tenant/integrations/releases/{release.json()['record_id']}",headers=self.other_headers)
        self.assertEqual(denied.status_code,404)
        system2=self.client.post("/tenant/systems",headers=self.headers,json={"system_id":"bank-v2","name":"Synthetic bank assistant","organization":"Test","jurisdiction":"SA","model_provider":"customer","model_version":"m2","prompt_version":"p2","retrieval_version":"r1","tool_version":"t1","policy_version":"pol1"})
        self.assertEqual(system2.status_code,200,system2.text)
        trial2=self.client.post("/tenant/trials",headers=self.headers,json={"system_id":"bank-v2","scenario_id":"disclosure-1","model_output":"Fees may apply."})
        self.assertEqual(trial2.status_code,200,trial2.text)
        release2=self.client.post("/tenant/releases",headers=self.headers,json={"system_id":"bank-v2","result_ids":[trial2.json()["result_id"]],"required_scenario_ids":["disclosure-1"],"scenario_set_version":"sa-v2","predecessor_record_id":release.json()["record_id"]})
        self.assertEqual(release2.status_code,200,release2.text)
        snapshot2=self.client.post("/tenant/systems/bank-v2/version-snapshots",headers=self.headers,json={"change_manifest":[{"component":"model","from_version":"m1","to_version":"m2","within_approved_boundary":True}],"predecessor_snapshot_id":snapshot.json()["snapshot_id"]})
        self.assertEqual(snapshot2.status_code,201,snapshot2.text)
        risk2=self.client.post(f"/tenant/releases/{release2.json()['record_id']}/risk-assessment",headers=self.headers,json={"snapshot_id":snapshot2.json()["snapshot_id"]})
        self.assertEqual(risk2.status_code,201,risk2.text)
        self.assertEqual(risk2.json()["release_path"],"MANDATORY_HUMAN_AUTHORIZATION")
        continuity=self.client.get(f"/tenant/releases/{release2.json()['record_id']}/continuity",headers=self.headers)
        self.assertEqual(continuity.status_code,200,continuity.text)
        self.assertEqual(len(continuity.json()["version_chain"]),2)
        self.assertEqual(len(continuity.json()["release_records"]),2)

if __name__ == "__main__":
    unittest.main()
