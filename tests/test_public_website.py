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

if __name__ == "__main__":
    unittest.main()
