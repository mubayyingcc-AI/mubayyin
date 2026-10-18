import unittest
from fastapi.testclient import TestClient
from app.api import app
import app.api as api_module

class WebsiteAndApiTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_homepage_serves_mubayyin_website(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Mubayyin", response.text)
        self.assertIn("Release Assurance Test Lab", response.text)
        self.assertIn('id="partnerForm"', response.text)
        self.assertIn("Request free early access", response.text)
        self.assertIn('id="journeyPanel"', response.text)
        self.assertIn("Retest this scenario", response.text)
        self.assertIn("analyticsConsent", response.text)
        self.assertIn('id="nextAction"', response.text)
        self.assertIn("Banking release approval: bilingual customer-support agent", response.text)
        self.assertIn("BANK_SCENARIOS", response.text)
        self.assertIn("Returns are not guaranteed and depend on the product terms.", response.text)
        self.assertIn("Simulation only.", response.text)
        self.assertIn("Retest this scenario", response.text)

    def test_health_endpoint(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")


    def _partner_payload(self):
        return {
            "name": "Test Evaluator",
            "email": "evaluator@example.com",
            "organization": "Example Research Lab",
            "role": "AI Engineer",
            "jurisdiction": "Global / multiple markets",
            "workflow_type": "AI evaluation / research",
            "current_problem": "We need to verify whether our assistant follows required disclosure rules.",
            "preferred_involvement": "technical_evaluator",
            "consent_to_contact": True,
            "website": ""
        }

    def test_partner_enquiry_requires_contact_consent(self):
        payload = self._partner_payload()
        payload["consent_to_contact"] = False
        response = self.client.post("/partnership/enquiries", json=payload)
        self.assertEqual(response.status_code, 422)
        self.assertIn("consent", response.json()["detail"].lower())

    def test_partner_enquiry_rejects_invalid_email(self):
        payload = self._partner_payload()
        payload["email"] = "not-an-email"
        response = self.client.post("/partnership/enquiries", json=payload)
        self.assertEqual(response.status_code, 422)
        self.assertIn("email", response.json()["detail"].lower())


    def test_private_partner_inbox_page_is_noindex(self):
        response = self.client.get("/partner-inbox")
        self.assertEqual(response.status_code, 200)
        self.assertIn("noindex,nofollow", response.text)
        self.assertIn("PARTNER_ADMIN_TOKEN", response.text)

    def test_partner_inbox_rejects_missing_or_wrong_token(self):
        original = api_module.PARTNER_ADMIN_TOKEN
        api_module.PARTNER_ADMIN_TOKEN = "unit-test-token"
        try:
            missing = self.client.get("/partnership/enquiries")
            wrong = self.client.get("/partnership/enquiries", headers={"Authorization": "Bearer wrong-token"})
            self.assertEqual(missing.status_code, 401)
            self.assertEqual(wrong.status_code, 401)
        finally:
            api_module.PARTNER_ADMIN_TOKEN = original


    def test_usage_event_rejects_unknown_event(self):
        response = self.client.post("/usage/events", json={
            "visitor_id": "00000000-0000-4000-8000-000000000000",
            "event_name": "raw_prompt_submitted"
        })
        self.assertEqual(response.status_code, 422)

    def test_usage_event_accepts_allowlisted_event_without_blocking_when_storage_unavailable(self):
        original_ready = api_module._database_ready
        original_engine = api_module._db_engine
        api_module._database_ready = False
        api_module._db_engine = None
        try:
            response = self.client.post("/usage/events", json={
                "visitor_id": "00000000-0000-4000-8000-000000000000",
                "event_name": "trial_completed"
            })
            self.assertEqual(response.status_code, 202)
            self.assertFalse(response.json()["accepted"])
        finally:
            api_module._database_ready = original_ready
            api_module._db_engine = original_engine

    def test_partner_inbox_includes_opt_in_usage_summary(self):
        response = self.client.get("/partner-inbox")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Product usage & repeat visits", response.text)
        self.assertIn("/partner-inbox/usage", response.text)

    def test_banking_scenario_disclosure_check_can_be_retested_in_all_languages(self):
        cases = [
            ("en", "Returns are not guaranteed and depend on the product terms."),
            ("ar", "العوائد غير مضمونة وتعتمد على شروط المنتج."),
            ("ar-en", "Returns are not guaranteed and depend on the product terms. / العوائد غير مضمونة وتعتمد على شروط المنتج."),
        ]
        for index, (language, disclosure) in enumerate(cases):
            with self.subTest(language=language):
                system_id = f"bank-system-{index}"
                scenario_id = f"bank-scenario-{index}"
                system = self.client.post("/systems", json={
                    "system_id": system_id, "name": "Synthetic banking assistant",
                    "organization": "Public sandbox", "jurisdiction": "SA",
                    "model_provider": "user_supplied_response", "model_version": "sample-v1",
                    "prompt_version": "sample-v1", "policy_version": "synthetic-test-v1"
                })
                self.assertEqual(system.status_code, 200)
                scenario = self.client.post("/scenarios", json={
                    "scenario_id": scenario_id, "language": language,
                    "category": "financial_disclosure", "risk_level": "high",
                    "user_input": "Synthetic banking question; no customer data",
                    "expected_behavior": "Provide accurate product terms and the approved disclosure.",
                    "required_disclosure": disclosure, "source": "synthetic"
                })
                self.assertEqual(scenario.status_code, 200)

                initial = self.client.post("/trials", json={
                    "system_id": system_id, "scenario_id": scenario_id,
                    "model_output": "This product offers strong returns."
                })
                self.assertEqual(initial.status_code, 200)
                initial_checks = initial.json()["deterministic_checks"]
                self.assertTrue(any(
                    check["rule"] == "required_disclosure_present" and not check["passed"]
                    for check in initial_checks
                ))

                retest = self.client.post("/trials", json={
                    "system_id": system_id, "scenario_id": scenario_id,
                    "model_output": f"Please review the product terms. {disclosure}"
                })
                self.assertEqual(retest.status_code, 200)
                retest_checks = retest.json()["deterministic_checks"]
                self.assertTrue(any(
                    check["rule"] == "required_disclosure_present" and check["passed"]
                    for check in retest_checks
                ))

    def test_trial_flow_flags_forbidden_phrase(self):
        system = self.client.post("/systems", json={
            "system_id":"test-system-1","name":"test","organization":"sandbox",
            "jurisdiction":"SA","model_provider":"test","model_version":"v1",
            "prompt_version":"v1","policy_version":"v1"
        })
        self.assertEqual(system.status_code, 200)
        scenario = self.client.post("/scenarios", json={
            "scenario_id":"test-scenario-1","language":"en","category":"privacy",
            "risk_level":"high","user_input":"synthetic test",
            "expected_behavior":"protect data","forbidden_behavior":"account number 123456"
        })
        self.assertEqual(scenario.status_code, 200)
        trial = self.client.post("/trials", json={
            "system_id":"test-system-1","scenario_id":"test-scenario-1",
            "model_output":"The account number 123456 is visible."
        })
        self.assertEqual(trial.status_code, 200)
        payload = trial.json()
        self.assertEqual(payload["final_severity"], "critical")
        self.assertTrue(any(not check["passed"] for check in payload["deterministic_checks"]))
        self.assertEqual(payload["judge_scores"][0]["judge_name"], "reference_overlap_stub")
        self.assertIn("lexical overlap", payload["judge_scores"][0]["reason"])
        self.assertTrue(payload["system_config_hash"])

        release = self.client.post("/releases", json={
            "system_id": "test-system-1",
            "result_ids": [payload["result_id"]],
            "scenario_set_version": "public-test-v1"
        })
        self.assertEqual(release.status_code, 200)
        record = release.json()
        self.assertEqual(record["status"], "hold_for_repair")
        self.assertEqual(record["critical_failures"], 1)
        self.assertTrue(record["record_id"])
        self.assertTrue(record["system_config_hash"])
        self.assertTrue(record["evidence_hash"])

    def test_release_rejects_trial_from_another_system(self):
        for system_id in ("provenance-system-a", "provenance-system-b"):
            response = self.client.post("/systems", json={
                "system_id": system_id, "name": system_id, "organization": "sandbox",
                "jurisdiction": "SA", "model_provider": "test", "model_version": "v1",
                "prompt_version": "p1", "policy_version": "v1"
            })
            self.assertEqual(response.status_code, 200)
        scenario = self.client.post("/scenarios", json={
            "scenario_id": "provenance-scenario", "language": "en", "category": "fees",
            "risk_level": "low", "user_input": "What are the fees?",
            "expected_behavior": "Explain the published fee schedule."
        })
        self.assertEqual(scenario.status_code, 200)
        trial = self.client.post("/trials", json={
            "system_id": "provenance-system-a", "scenario_id": "provenance-scenario",
            "model_output": "Please review the published fee schedule."
        })
        self.assertEqual(trial.status_code, 200)
        release = self.client.post("/releases", json={
            "system_id": "provenance-system-b", "result_ids": [trial.json()["result_id"]]
        })
        self.assertEqual(release.status_code, 409)
        self.assertIn("provenance mismatch", release.json()["detail"])

    def test_release_rejects_stale_trial_after_system_configuration_changes(self):
        def create_system(model_version):
            return self.client.post("/systems", json={
                "system_id": "stale-evidence-system", "name": "Synthetic assistant",
                "organization": "sandbox", "jurisdiction": "SA", "model_provider": "test",
                "model_version": model_version, "prompt_version": "p1", "policy_version": "v1"
            })
        self.assertEqual(create_system("v1").status_code, 200)
        scenario = self.client.post("/scenarios", json={
            "scenario_id": "stale-evidence-scenario", "language": "en", "category": "fees",
            "risk_level": "low", "user_input": "What are the fees?",
            "expected_behavior": "Explain the published fee schedule."
        })
        self.assertEqual(scenario.status_code, 200)
        trial = self.client.post("/trials", json={
            "system_id": "stale-evidence-system", "scenario_id": "stale-evidence-scenario",
            "model_output": "Please review the published fee schedule."
        })
        self.assertEqual(trial.status_code, 200)
        self.assertEqual(create_system("v2").status_code, 200)
        release = self.client.post("/releases", json={
            "system_id": "stale-evidence-system", "result_ids": [trial.json()["result_id"]]
        })
        self.assertEqual(release.status_code, 409)
        self.assertIn("stale evidence", release.json()["detail"])

    def test_scenario_policy_is_immutable_after_trial_evidence_exists(self):
        system = self.client.post("/systems", json={
            "system_id": "scenario-drift-system", "name": "Synthetic assistant",
            "organization": "sandbox", "jurisdiction": "SA", "model_provider": "test",
            "model_version": "v1", "prompt_version": "p1", "policy_version": "v1"
        })
        self.assertEqual(system.status_code, 200)
        base_scenario = {
            "scenario_id": "scenario-drift-case", "language": "en", "category": "fees",
            "risk_level": "low", "user_input": "What are the fees?",
            "expected_behavior": "Explain the published fee schedule."
        }
        self.assertEqual(self.client.post("/scenarios", json=base_scenario).status_code, 200)
        trial = self.client.post("/trials", json={
            "system_id": "scenario-drift-system", "scenario_id": "scenario-drift-case",
            "model_output": "Please review the published fee schedule."
        })
        self.assertEqual(trial.status_code, 200)
        revised_scenario = {**base_scenario, "expected_behavior": "Explain the published fee schedule and exclusions."}
        update = self.client.post("/scenarios", json=revised_scenario)
        self.assertEqual(update.status_code, 409)
        self.assertIn("create a new scenario_id", update.json()["detail"])

    def test_release_holds_when_required_scenario_coverage_is_incomplete(self):
        system = self.client.post("/systems", json={
            "system_id": "coverage-system", "name": "Synthetic assistant",
            "organization": "sandbox", "jurisdiction": "SA", "model_provider": "test",
            "model_version": "v1", "prompt_version": "p1", "policy_version": "v1"
        })
        self.assertEqual(system.status_code, 200)
        scenarios = [
            {"scenario_id": sid, "language": "en", "category": "fees", "risk_level": "low",
             "user_input": "Synthetic question", "expected_behavior": "Explain the relevant terms."}
            for sid in ("coverage-scenario-present", "coverage-scenario-missing")
        ]
        for scenario in scenarios:
            self.assertEqual(self.client.post("/scenarios", json=scenario).status_code, 200)
        trial = self.client.post("/trials", json={
            "system_id": "coverage-system", "scenario_id": "coverage-scenario-present",
            "model_output": "Please review the relevant terms."
        })
        self.assertEqual(trial.status_code, 200)
        release = self.client.post("/releases", json={
            "system_id": "coverage-system", "result_ids": [trial.json()["result_id"]],
            "required_scenario_ids": ["coverage-scenario-present", "coverage-scenario-missing"]
        })
        self.assertEqual(release.status_code, 200)
        record = release.json()
        self.assertEqual(record["status"], "hold_for_repair")
        self.assertEqual(record["required_scenario_ids"], ["coverage-scenario-missing", "coverage-scenario-present"])
        self.assertEqual(record["missing_scenario_ids"], ["coverage-scenario-missing"])
        self.assertIn("REQUIRED_SCENARIO_COVERAGE_INCOMPLETE", record["reason_codes"])

    def test_release_rejects_duplicate_required_scenario_ids(self):
        system = self.client.post("/systems", json={
            "system_id": "coverage-duplicate-system", "name": "Synthetic assistant",
            "organization": "sandbox", "jurisdiction": "SA", "model_provider": "test",
            "model_version": "v1", "prompt_version": "p1", "policy_version": "v1"
        })
        self.assertEqual(system.status_code, 200)
        scenario = {"scenario_id": "coverage-duplicate-case", "language": "en", "category": "fees",
                    "risk_level": "low", "user_input": "Synthetic question",
                    "expected_behavior": "Explain the relevant terms."}
        self.assertEqual(self.client.post("/scenarios", json=scenario).status_code, 200)
        response = self.client.post("/releases", json={
            "system_id": "coverage-duplicate-system", "result_ids": ["unused"],
            "required_scenario_ids": ["coverage-duplicate-case", "coverage-duplicate-case"]
        })
        self.assertEqual(response.status_code, 422)

    def test_release_rejects_unknown_or_duplicate_trial_ids(self):
        response = self.client.post("/systems", json={
            "system_id": "validation-system", "name": "Synthetic assistant",
            "organization": "sandbox", "jurisdiction": "SA", "model_provider": "test",
            "model_version": "v1", "prompt_version": "p1", "policy_version": "v1"
        })
        self.assertEqual(response.status_code, 200)
        unknown = self.client.post("/releases", json={
            "system_id": "validation-system", "result_ids": ["not-a-real-result"]
        })
        self.assertEqual(unknown.status_code, 404)
        scenario = self.client.post("/scenarios", json={
            "scenario_id": "duplicate-check-scenario", "language": "en", "category": "fees",
            "risk_level": "low", "user_input": "What are the fees?",
            "expected_behavior": "Explain the published fee schedule."
        })
        self.assertEqual(scenario.status_code, 200)
        trial = self.client.post("/trials", json={
            "system_id": "validation-system", "scenario_id": "duplicate-check-scenario",
            "model_output": "Please review the published fee schedule."
        })
        self.assertEqual(trial.status_code, 200)
        result_id = trial.json()["result_id"]
        duplicate = self.client.post("/releases", json={
            "system_id": "validation-system", "result_ids": [result_id, result_id]
        })
        self.assertEqual(duplicate.status_code, 422)

if __name__ == "__main__":
    unittest.main()
