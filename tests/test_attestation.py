import unittest
from unittest.mock import patch

from app.services.attestation import create_release_bundle, verify_release_bundle


class ReleaseAttestationTests(unittest.TestCase):
    def setUp(self):
        self.record = {
            "record_id": "mrr_test123",
            "system_id": "synthetic-system",
            "status": "hold_for_repair",
            "reason_codes": ["REQUIRED_SCENARIO_COVERAGE_INCOMPLETE"],
            "required_scenario_ids": ["scenario-a", "scenario-b"],
            "missing_scenario_ids": ["scenario-b"],
            "created_at": 123.0,
        }

    def test_unsigned_bundle_detects_payload_tampering(self):
        bundle = create_release_bundle(self.record, signing_key="")
        valid = verify_release_bundle(bundle, signing_key="")
        self.assertTrue(valid["integrity_valid"])
        self.assertFalse(valid["authenticity_verified"])
        self.assertEqual(valid["status"], "integrity_valid_unsigned")

        bundle["record"]["status"] = "safe_to_serve"
        tampered = verify_release_bundle(bundle, signing_key="")
        self.assertFalse(tampered["integrity_valid"])
        self.assertEqual(tampered["status"], "payload_hash_mismatch")


    def test_evidence_is_bound_to_the_bundle_hash(self):
        bundle = create_release_bundle(
            self.record,
            evidence={"trials": [{"result_id": "trial-1", "model_output": "synthetic output"}]},
            signing_key="",
        )
        self.assertTrue(verify_release_bundle(bundle, signing_key="")["integrity_valid"])
        bundle["evidence"]["trials"][0]["model_output"] = "changed after export"
        result = verify_release_bundle(bundle, signing_key="")
        self.assertFalse(result["integrity_valid"])
        self.assertEqual(result["status"], "payload_hash_mismatch")

    def test_hmac_bundle_requires_the_correct_key(self):
        bundle = create_release_bundle(self.record, signing_key="test-secret-key")
        verified = verify_release_bundle(bundle, signing_key="test-secret-key")
        self.assertTrue(verified["valid"])
        self.assertTrue(verified["authenticity_verified"])

        wrong_key = verify_release_bundle(bundle, signing_key="wrong-key")
        self.assertFalse(wrong_key["valid"])
        self.assertEqual(wrong_key["signature_status"], "invalid")

    def test_signed_bundle_without_key_is_not_called_authentic(self):
        bundle = create_release_bundle(self.record, signing_key="test-secret-key")
        result = verify_release_bundle(bundle, signing_key="")
        self.assertTrue(result["integrity_valid"])
        self.assertFalse(result["authenticity_verified"])
        self.assertEqual(result["signature_status"], "key_unavailable")

    def test_canonical_hash_is_independent_of_dictionary_key_order(self):
        first = create_release_bundle({"a": 1, "b": 2}, signing_key="")
        second = create_release_bundle({"b": 2, "a": 1}, signing_key="")
        self.assertEqual(first["integrity"]["payload_hash"], second["integrity"]["payload_hash"])

    def test_unsupported_schema_is_rejected(self):
        result = verify_release_bundle({"schema_version": "future-version"})
        self.assertFalse(result["valid"])
        self.assertEqual(result["status"], "unsupported_schema")


if __name__ == "__main__":
    unittest.main()
