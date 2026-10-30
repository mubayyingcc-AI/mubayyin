import unittest
from types import SimpleNamespace
from app.services.release_governance import assess_release_path, classify_change_manifest, create_version_snapshot, build_release_interoperability_payload

class ReleaseGovernanceTests(unittest.TestCase):
    def setUp(self):
        self.system = SimpleNamespace(system_id="bank-assistant-v2", model_provider="customer", model_version="model-2", prompt_version="prompt-2", retrieval_version="kb-2", tool_version="tools-1", policy_version="policy-1", config_hash=lambda: "a" * 64)
    def test_routine_in_boundary_change_is_tier_one(self):
        tier, _ = classify_change_manifest([{"component":"logging","from_version":"1","to_version":"2","within_approved_boundary":True}])
        self.assertEqual(tier, "TIER_1")
    def test_prompt_change_requires_review(self):
        tier, _ = classify_change_manifest([{"component":"prompt","from_version":"1","to_version":"2","within_approved_boundary":True}])
        self.assertEqual(tier, "TIER_2")
    def test_tool_permission_expansion_requires_human_authorization(self):
        result = assess_release_path(system_id="bank-assistant-v2",snapshot_hash="b"*64,manifest=[{"component":"tool","from_version":"1","to_version":"2","within_approved_boundary":True,"permission_expansion":True}],base_release_status="safe_to_serve",critical_failures=0,major_failures=0,evidence_complete=True,mandatory_checks_passed=True)
        self.assertEqual(result.risk_tier,"TIER_3")
        self.assertEqual(result.release_path,"MANDATORY_HUMAN_AUTHORIZATION")
    def test_unknown_change_fails_closed(self):
        tier,_=classify_change_manifest([{"component":"unknown_runtime_magic","to_version":"x","within_approved_boundary":True}])
        self.assertEqual(tier,"TIER_4_UNCERTAIN")
    def test_empty_manifest_cannot_fast_track(self):
        result=assess_release_path(system_id="s",snapshot_hash="b"*64,manifest=[],base_release_status="safe_to_serve",critical_failures=0,major_failures=0,evidence_complete=True,mandatory_checks_passed=True)
        self.assertEqual(result.effective_release_state,"HOLD_FOR_REPAIR")
    def test_critical_failure_overrides_routine_fast_track(self):
        result=assess_release_path(system_id="s",snapshot_hash="b"*64,manifest=[{"component":"logging","to_version":"2","within_approved_boundary":True}],base_release_status="safe_to_serve",critical_failures=1,major_failures=0,evidence_complete=True,mandatory_checks_passed=True)
        self.assertNotEqual(result.release_path,"AUTOMATED_FAST_TRACK_ELIGIBLE")
    def test_incomplete_evidence_holds(self):
        result=assess_release_path(system_id="s",snapshot_hash="b"*64,manifest=[{"component":"logging","to_version":"2","within_approved_boundary":True}],base_release_status="safe_to_serve",critical_failures=0,major_failures=0,evidence_complete=False,mandatory_checks_passed=True)
        self.assertEqual(result.release_path,"HOLD_FOR_EVIDENCE")
    def test_snapshot_hash_binds_manifest_and_predecessor(self):
        first=create_version_snapshot(self.system,[])
        second=create_version_snapshot(self.system,[{"component":"prompt","from_version":"prompt-1","to_version":"prompt-2","within_approved_boundary":True}],predecessor_system_id="bank-assistant-v1",predecessor_snapshot_hash="c"*64)
        self.assertNotEqual(first.snapshot_hash,second.snapshot_hash)
    def test_snapshot_rejects_missing_boundary_fact(self):
        with self.assertRaises(ValueError):
            create_version_snapshot(self.system,[{"component":"prompt","to_version":"2"}])
    def test_interoperability_contract_is_versioned(self):
        payload=build_release_interoperability_payload({"record_id":"mrr_1"},None,{"previous":None},None)
        self.assertEqual(payload["schema_version"],"mubayyin.enterprise-release.v1")

if __name__ == "__main__":
    unittest.main()
