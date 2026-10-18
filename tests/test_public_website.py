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
        self.assertIsNone(payload["judge_scores"][0]["language_quality"])
        self.assertIsNone(payload["judge_scores"][0]["privacy_behavior"])
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


    def test_arabic_gcc_page_serves_right_to_left_and_links_to_english(self):
        response = self.client.get("/ar")
        self.assertEqual(response.status_code, 200)
        self.assertIn('lang="ar" dir="rtl"', response.text)
        self.assertIn('href="/"', response.text)
        self.assertIn("تشغيل الاختبار المجاني", response.text)
        self.assertIn("/systems", response.text)
        self.assertIn("/scenarios", response.text)
        self.assertIn("/trials", response.text)
        self.assertIn("/releases", response.text)

    def test_readiness_endpoint_reports_storage_mode(self):
        response = self.client.get("/ready")
        self.assertIn(response.status_code, (200, 503))
        if response.status_code == 200:
            self.assertIn(response.json()["database"], ("ready", "memory_only"))

    def test_release_rejects_duplicate_trial_ids(self):
        self.client.post("/systems", json={
            "system_id": "dup-release-system", "name": "test", "organization": "sandbox",
            "jurisdiction": "SA", "model_provider": "test", "model_version": "v1",
            "prompt_version": "v1", "policy_version": "v1"
        })
        self.client.post("/scenarios", json={
            "scenario_id": "dup-release-scenario", "language": "ar", "category": "disclosure",
            "risk_level": "low", "user_input": "synthetic", "expected_behavior": "disclose"
        })
        trial = self.client.post("/trials", json={
            "system_id": "dup-release-system", "scenario_id": "dup-release-scenario",
            "model_output": "sample output"
        })
        self.assertEqual(trial.status_code, 200)
        rid = trial.json()["result_id"]
        response = self.client.post("/releases", json={
            "system_id": "dup-release-system", "result_ids": [rid, rid]
        })
        self.assertEqual(response.status_code, 422)

    def test_release_rejects_trial_evidence_from_another_system(self):
        for system_id in ("owner-system-a", "owner-system-b"):
            self.client.post("/systems", json={
                "system_id": system_id, "name": system_id, "organization": "sandbox",
                "jurisdiction": "SA", "model_provider": "test", "model_version": "v1",
                "prompt_version": "v1", "policy_version": "v1"
            })
        self.client.post("/scenarios", json={
            "scenario_id": "owner-scenario", "language": "en", "category": "disclosure",
            "risk_level": "low", "user_input": "synthetic", "expected_behavior": "disclose"
        })
        trial = self.client.post("/trials", json={
            "system_id": "owner-system-a", "scenario_id": "owner-scenario",
            "model_output": "sample output"
        })
        self.assertEqual(trial.status_code, 200)
        response = self.client.post("/releases", json={
            "system_id": "owner-system-b", "result_ids": [trial.json()["result_id"]]
        })
        self.assertEqual(response.status_code, 409)


    def test_human_review_cannot_mutate_evidence_after_release_record_creation(self):
        self.client.post("/systems", json={
            "system_id": "immutable-review-system", "name": "test", "organization": "sandbox",
            "jurisdiction": "SA", "model_provider": "test", "model_version": "v1",
            "prompt_version": "v1", "policy_version": "v1"
        })
        self.client.post("/scenarios", json={
            "scenario_id": "immutable-review-scenario", "language": "en", "category": "disclosure",
            "risk_level": "low", "user_input": "synthetic", "expected_behavior": "disclose"
        })
        trial = self.client.post("/trials", json={
            "system_id": "immutable-review-system", "scenario_id": "immutable-review-scenario",
            "model_output": "sample output"
        })
        self.assertEqual(trial.status_code, 200)
        rid = trial.json()["result_id"]
        release = self.client.post("/releases", json={
            "system_id": "immutable-review-system", "result_ids": [rid]
        })
        self.assertEqual(release.status_code, 200)
        review = self.client.post(f"/trials/{rid}/review", json={
            "reviewer": "Test reviewer", "agrees_with_automation": True, "comment": "late review"
        })
        self.assertEqual(review.status_code, 409)


    def test_release_holds_when_required_scenario_coverage_is_missing(self):
        self.client.post("/systems", json={
            "system_id": "coverage-system", "name": "test", "organization": "sandbox",
            "jurisdiction": "SA", "model_provider": "test", "model_version": "v1",
            "prompt_version": "v1", "policy_version": "v1"
        })
        for scenario_id in ("coverage-scenario-a", "coverage-scenario-b"):
            self.client.post("/scenarios", json={
                "scenario_id": scenario_id, "language": "ar", "category": "disclosure",
                "risk_level": "low", "user_input": "synthetic", "expected_behavior": "disclose"
            })
        trial = self.client.post("/trials", json={
            "system_id": "coverage-system", "scenario_id": "coverage-scenario-a",
            "model_output": "sample output"
        })
        self.assertEqual(trial.status_code, 200)
        response = self.client.post("/releases", json={
            "system_id": "coverage-system", "result_ids": [trial.json()["result_id"]],
            "required_scenario_ids": ["coverage-scenario-a", "coverage-scenario-b"],
            "scenario_set_version": "sa-banking-v1"
        })
        self.assertEqual(response.status_code, 200)
        record = response.json()
        self.assertEqual(record["status"], "hold_for_repair")
        self.assertEqual(record["required_scenario_ids"], ["coverage-scenario-a", "coverage-scenario-b"])
        self.assertEqual(record["missing_scenario_ids"], ["coverage-scenario-b"])
        self.assertIn("REQUIRED_SCENARIO_COVERAGE_INCOMPLETE", record["reason_codes"])


    def test_release_comparison_reports_evidence_and_decision_changes(self):
        self.client.post("/systems", json={
            "system_id": "compare-system", "name": "test", "organization": "sandbox",
            "jurisdiction": "SA", "model_provider": "test", "model_version": "v1",
            "prompt_version": "v1", "policy_version": "v1"
        })
        self.client.post("/scenarios", json={
            "scenario_id": "compare-scenario", "language": "en", "category": "disclosure",
            "risk_level": "low", "user_input": "synthetic", "expected_behavior": "disclose"
        })
        first = self.client.post("/trials", json={
            "system_id": "compare-system", "scenario_id": "compare-scenario",
            "model_output": "I disclose the approved terms."
        })
        self.assertEqual(first.status_code, 200)
        base = self.client.post("/releases", json={
            "system_id": "compare-system", "result_ids": [first.json()["result_id"]],
            "scenario_set_version": "comparison-v1", "required_scenario_ids": ["compare-scenario"]
        })
        self.assertEqual(base.status_code, 200)
        second = self.client.post("/trials", json={
            "system_id": "compare-system", "scenario_id": "compare-scenario",
            "model_output": "Different answer with no disclosure."
        })
        self.assertEqual(second.status_code, 200)
        candidate = self.client.post("/releases", json={
            "system_id": "compare-system", "result_ids": [second.json()["result_id"]],
            "scenario_set_version": "comparison-v1", "required_scenario_ids": ["compare-scenario"]
        })
        self.assertEqual(candidate.status_code, 200)
        response = self.client.get(
            f'/releases/{base.json()["record_id"]}/compare/{candidate.json()["record_id"]}'
        )
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertTrue(result["comparison"]["evidence_changed"])
        self.assertIn(second.json()["result_id"], result["comparison"]["added_trial_result_ids"])
        self.assertIn("interpretation", result["comparison"])

if __name__ == "__main__":
    unittest.main()
