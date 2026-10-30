import unittest
from unittest.mock import patch
from datetime import datetime, timezone

from app import api

class ActionMandateApiTests(unittest.TestCase):
    def setUp(self):
        self.rows = {}
        self.auth = patch.object(api, "_require_tenant", return_value="tenant-test")
        self.auth.start()
        self.addCleanup(self.auth.stop)
        def store(tenant, kind, rid, sid, payload, immutable=False):
            key=(tenant,kind,rid)
            if immutable and key in self.rows:
                from fastapi import HTTPException
                raise HTTPException(409, "duplicate")
            self.rows[key]=payload
        def get(tenant, kind, rid):
            return self.rows.get((tenant,kind,rid))
        self.store_patch=patch.object(api,"_tenant_store",side_effect=store)
        self.get_patch=patch.object(api,"_tenant_get",side_effect=get)
        self.store_patch.start(); self.get_patch.start()
        self.addCleanup(self.store_patch.stop); self.addCleanup(self.get_patch.stop)

    def create_mandate(self):
        req=api.CreateActionMandateRequest(
            mandate_id="m-1",mandate_version="1",policy_version="p-1",
            principal_id="customer-1",authorised_actor_id="agent-1",
            permitted_actions=["prepare_refund"],resource_id="case-1",
            currency="AED",maximum_amount="100",
            issued_at="2026-10-01T00:00:00+00:00",
            expires_at="2026-11-01T00:00:00+00:00")
        return api.tenant_create_action_mandate(req)

    def test_create_mandate_stores_tenant_scoped_immutable_record(self):
        result=self.create_mandate()
        self.assertEqual(result["mandate_id"],"m-1")
        self.assertIn(("tenant-test","action_mandate","m-1"),self.rows)

    def test_assessment_uses_stored_mandate_and_returns_evidence(self):
        self.create_mandate()
        req=api.AssessActionRequest(
            mandate_id="m-1",request_id="r-1",principal_id="customer-1",
            actor_id="agent-1",action_type="prepare_refund",resource_id="case-1",
            currency="AED",amount="50",proposed_at=datetime.now(timezone.utc).isoformat())
        result=api.tenant_assess_action(req)
        self.assertIn(result["decision"],("permitted","review_required","rejected"))
        self.assertTrue(result["evidence_fingerprint"])
        self.assertIn(("tenant-test","action_assessment",result["assessment_id"]),self.rows)

    def test_revocation_is_recorded_and_subsequent_assessment_rejected(self):
        self.create_mandate()
        api.tenant_revoke_action_mandate("m-1")
        req=api.AssessActionRequest(
            mandate_id="m-1",request_id="r-2",principal_id="customer-1",
            actor_id="agent-1",action_type="prepare_refund",resource_id="case-1",
            currency="AED",amount="50",proposed_at=datetime.now(timezone.utc).isoformat())
        result=api.tenant_assess_action(req)
        self.assertEqual(result["decision"],"rejected")
        self.assertIn("MANDATE_REVOKED",result["reason_codes"])

if __name__ == "__main__":
    unittest.main()
