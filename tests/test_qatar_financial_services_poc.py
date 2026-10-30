import unittest

from app.models.core import AISystem, ReleaseStatus
from app.services.evaluator import run_trial
from app.services.release_gate import ReleaseThresholds, decide_release
from scenarios.qatar_financial_services_poc import BASELINE_OUTPUTS, REPAIRED_OUTPUTS, SCENARIOS


class QatarFinancialServicesPoCTests(unittest.TestCase):
    def setUp(self):
        self.system = AISystem(
            system_id="qa-poc-test",
            name="Synthetic bilingual financial services assistant",
            organization="Mubayyin PoC",
            jurisdiction="QA",
            model_provider="synthetic-fixture",
            model_version="v1",
            prompt_version="p1",
            policy_version="qa-poc-v1",
        )
        self.thresholds = ReleaseThresholds(max_critical_failures=0, max_major_failures=0)
        self.required = [scenario.scenario_id for scenario in SCENARIOS]

    def run_set(self, outputs):
        results = []
        for scenario in SCENARIOS:
            result = run_trial(scenario, outputs[scenario.scenario_id])
            result.system_config_hash = self.system.config_hash()
            results.append(result)
        return results

    def test_pack_has_twelve_unique_synthetic_qatar_scenarios(self):
        self.assertEqual(len(SCENARIOS), 12)
        self.assertEqual(len({scenario.scenario_id for scenario in SCENARIOS}), 12)
        self.assertTrue(all(scenario.source == "synthetic" for scenario in SCENARIOS))
        self.assertTrue(all(scenario.language in {"ar", "en", "ar-en"} for scenario in SCENARIOS))
        privacy = [scenario for scenario in SCENARIOS if scenario.category == "privacy"]
        self.assertTrue(privacy)
        self.assertTrue(all(scenario.sensitive_markers for scenario in privacy))

    def test_baseline_demo_holds_on_critical_findings(self):
        results = self.run_set(BASELINE_OUTPUTS)
        record = decide_release(
            self.system, results, self.thresholds, approver=None,
            scenario_set_version="qa-financial-poc-v1",
            required_scenario_ids=self.required,
        )
        self.assertEqual(record.status, ReleaseStatus.HOLD_FOR_REPAIR)
        self.assertGreater(record.critical_failures, 0)

    def test_missing_required_scenario_coverage_holds(self):
        results = self.run_set(REPAIRED_OUTPUTS)
        record = decide_release(
            self.system, results[:-1], self.thresholds, approver=None,
            scenario_set_version="qa-financial-poc-v1",
            required_scenario_ids=self.required,
        )
        self.assertEqual(record.status, ReleaseStatus.HOLD_FOR_REPAIR)
        self.assertEqual(record.missing_scenario_ids, [self.required[-1]])

    def test_repaired_demo_removes_configured_deterministic_failures(self):
        results = self.run_set(REPAIRED_OUTPUTS)
        failures = [check for result in results for check in result.deterministic_checks if not check.passed]
        self.assertEqual(failures, [])
        record = decide_release(
            self.system, results, self.thresholds, approver="Synthetic PoC reviewer",
            scenario_set_version="qa-financial-poc-v1",
            required_scenario_ids=self.required,
        )
        self.assertEqual(record.missing_scenario_ids, [])
        self.assertEqual(record.critical_failures, 0)


if __name__ == "__main__":
    unittest.main()
