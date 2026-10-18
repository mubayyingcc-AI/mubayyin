import unittest
from fastapi.testclient import TestClient
from app.api import app

class WebsiteAndApiTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_homepage_serves_mubayyin_website(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Mubayyin", response.text)
        self.assertIn("Release Assurance Test Lab", response.text)

    def test_health_endpoint(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

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

if __name__ == "__main__":
    unittest.main()
