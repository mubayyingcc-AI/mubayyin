import unittest

from app.services.assurance_workstreams import (
    normalize_arabic_text, evaluate_bilingual_financial_output,
    create_evidence_manifest, verify_evidence_manifest,
    compare_behaviour_runs, decide_assurance, build_retest_event,
    run_five_workstream_assessment,
)


class TestFiveAssuranceWorkstreams(unittest.TestCase):
    def test_arabic_normalisation_digits_and_diacritics(self):
        self.assertEqual(normalize_arabic_text("إيداع ١٢٣ ر.س"), normalize_arabic_text("ايداع 123 ر.س"))

    def test_bilingual_literal_financial_checks(self):
        result = evaluate_bilingual_financial_output(
            "تم استلام مبلغ ١٢٥٠ ريال",
            required_terms=["استلام"], required_values=["1250"], prohibited_terms=["مضمون"],
        )
        self.assertTrue(result["passed"])
        self.assertEqual(result["failed_count"], 0)

    def test_evidence_manifest_detects_tampering_and_authenticates_hmac(self):
        manifest = create_evidence_manifest(
            {"result": "pass"}, system_snapshot_hash="snap-a",
            scenario_set_version="bench-1", policy_version="p1",
            issuer="runner-a", signing_key="test-secret", created_at="2026-01-01T00:00:00Z",
        )
        self.assertTrue(verify_evidence_manifest(manifest, signing_key="test-secret")["valid"])
        altered = {**manifest, "evidence": {"result": "changed"}}
        self.assertFalse(verify_evidence_manifest(altered, signing_key="test-secret")["valid"])
        self.assertFalse(verify_evidence_manifest(manifest, signing_key="wrong")["valid"])

    def test_behaviour_diff_finds_regression_and_missing_case(self):
        result = compare_behaviour_runs(
            {"run_id": "base", "scenarios": {"a": "none", "b": "major", "c": "minor"}},
            {"run_id": "new", "scenarios": {"a": "critical", "b": "none"}},
        )
        self.assertEqual(result["regression_count"], 1)
        self.assertEqual(result["missing_or_unscorable"], ["c"])

    def test_decision_fails_closed_for_incomplete_evidence_and_regression(self):
        result = decide_assurance(check_results=[], evidence_complete=False, regression_count=1)
        self.assertEqual(result["status"], "hold_for_repair")
        self.assertIn("EVIDENCE_INCOMPLETE", result["reasons"])

    def test_human_approval_can_make_decision_conditional(self):
        result = decide_assurance(
            check_results=[], evidence_complete=True,
            require_human_approval=True, human_approval=False,
        )
        self.assertEqual(result["status"], "conditional_serve")

    def test_retest_event_is_stable_and_idempotent(self):
        args = dict(tenant_ref="tenant-a", system_ref="system-a",
                    previous_snapshot_hash="old", current_snapshot_hash="new",
                    changed_components=["prompt", "model"])
        first, second = build_retest_event(**args), build_retest_event(**args)
        self.assertEqual(first["event_id"], second["event_id"])
        self.assertEqual(first["idempotency_key"], second["idempotency_key"])
        self.assertTrue(first["retest_required"])

    def test_non_material_change_does_not_trigger_retest(self):
        event = build_retest_event(
            tenant_ref="tenant-a", system_ref="system-a",
            previous_snapshot_hash="old", current_snapshot_hash="new",
            changed_components=["display", "logging"],
        )
        self.assertFalse(event["retest_required"])

    def test_integrated_orchestrator_connects_workstreams(self):
        result = run_five_workstream_assessment(
            output="Payment received 1250 ريال",
            required_terms=["received"], required_values=["1250"],
            baseline_run={"run_id": "b", "scenarios": {"s1": "none"}},
            candidate_run={"run_id": "c", "scenarios": {"s1": "major"}},
            evidence_complete=True, signing_key="secret",
            system_snapshot_hash="snapshot", scenario_set_version="v1",
            policy_version="p1",
        )
        self.assertEqual(result["decision"]["status"], "hold_for_repair")
        self.assertTrue(result["workstreams"]["wp2_evidence_integrity"]["signed"])
        self.assertEqual(result["workstreams"]["wp3_behaviour_change_intelligence"]["regression_count"], 1)


if __name__ == "__main__":
    unittest.main()
