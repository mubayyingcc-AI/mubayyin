import unittest
from unittest.mock import patch
from sdk.python.mubayyin_client import MubayyinClient

class EnterpriseGovernanceSDKTests(unittest.TestCase):
    def setUp(self):
        self.client=MubayyinClient("https://example.invalid","x"*40)
    def test_snapshot_creation_uses_tenant_api(self):
        with patch.object(self.client,"_request",return_value={"snapshot_id":"snp_1"}) as call:
            result=self.client.create_version_snapshot("system-v2",[{"component":"logging","to_version":"2","within_approved_boundary":True}])
        self.assertEqual(result["snapshot_id"],"snp_1")
        self.assertEqual(call.call_args.args[:2],("POST","/tenant/systems/system-v2/version-snapshots"))
    def test_risk_assessment_uses_versioned_record_route(self):
        with patch.object(self.client,"_request",return_value={"release_path":"HUMAN_REVIEW_REQUIRED"}) as call:
            result=self.client.assess_release_path("mrr_1","snp_1")
        self.assertEqual(result["release_path"],"HUMAN_REVIEW_REQUIRED")
        self.assertEqual(call.call_args.args[:2],("POST","/tenant/releases/mrr_1/risk-assessment"))
    def test_interoperability_is_read_only(self):
        with patch.object(self.client,"_request",return_value={"schema_version":"mubayyin.enterprise-release.v1"}) as call:
            self.client.get_interoperability_release("mrr_1")
        self.assertEqual(call.call_args.args[:2],("GET","/tenant/integrations/releases/mrr_1"))

if __name__ == "__main__":
    unittest.main()
