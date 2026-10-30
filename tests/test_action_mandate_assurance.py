import unittest
from dataclasses import replace
from app.services.action_mandate_assurance import ActionDecision, ActionMandate, MandateState, ProposedAction, assess_action

NOW = "2026-10-30T12:00:00+00:00"

def mandate(**changes):
    base = ActionMandate(
        mandate_id="mandate-001", mandate_version="3", policy_version="policy-7",
        principal_id="customer-123", authorised_actor_id="agent-1",
        permitted_actions=("prepare_refund",), resource_id="case-88",
        currency="AED", maximum_amount="500.00",
        issued_at="2026-10-01T00:00:00+00:00", expires_at="2026-11-01T00:00:00+00:00")
    return replace(base, **changes)

def proposal(**changes):
    base = ProposedAction(
        request_id="request-001", principal_id="customer-123", actor_id="agent-1",
        action_type="prepare_refund", resource_id="case-88", currency="AED",
        amount="250.00", proposed_at=NOW)
    return replace(base, **changes)

class ActionMandateAssuranceTests(unittest.TestCase):
    def test_matching_current_mandate_is_permitted(self):
        self.assertEqual(assess_action(mandate(), proposal(), NOW).decision, ActionDecision.PERMITTED)
    def test_revoked_mandate_is_rejected(self):
        m = mandate(state=MandateState.REVOKED, revoked_at="2026-10-29T10:00:00+00:00")
        self.assertEqual(assess_action(m, proposal(), NOW).decision, ActionDecision.REJECTED)
    def test_expired_mandate_is_rejected(self):
        m = mandate(expires_at="2026-10-29T00:00:00+00:00")
        self.assertIn("MANDATE_EXPIRED", assess_action(m, proposal(), NOW).reason_codes)
    def test_changed_resource_is_rejected(self):
        r = assess_action(mandate(), proposal(resource_id="new-beneficiary"), NOW)
        self.assertIn("RESOURCE_MISMATCH", r.reason_codes)
        self.assertEqual(r.decision, ActionDecision.REJECTED)
    def test_amount_above_limit_is_rejected(self):
        self.assertIn("AMOUNT_EXCEEDS_LIMIT", assess_action(mandate(), proposal(amount="500.01"), NOW).reason_codes)
    def test_currency_change_is_rejected(self):
        self.assertIn("CURRENCY_MISMATCH", assess_action(mandate(), proposal(currency="SAR"), NOW).reason_codes)
    def test_unauthorised_actor_is_rejected(self):
        self.assertIn("ACTOR_NOT_AUTHORISED", assess_action(mandate(), proposal(actor_id="agent-2"), NOW).reason_codes)
    def test_permitted_delegate_is_accepted_only_when_named(self):
        m = mandate(permitted_delegates=("agent-2",))
        p = proposal(actor_id="agent-2", delegation_path=("agent-2",))
        self.assertEqual(assess_action(m, p, NOW).decision, ActionDecision.PERMITTED)
    def test_unapproved_delegation_is_rejected(self):
        p = proposal(actor_id="agent-2", delegation_path=("agent-2",))
        self.assertIn("ACTOR_NOT_AUTHORISED", assess_action(mandate(), p, NOW).reason_codes)
    def test_duplicate_execution_signal_is_rejected(self):
        self.assertIn("POSSIBLE_DUPLICATE_EXECUTION", assess_action(mandate(), proposal(prior_execution_detected=True), NOW).reason_codes)
    def test_incomplete_context_requires_review(self):
        self.assertEqual(assess_action(mandate(), proposal(context_complete=False), NOW).decision, ActionDecision.REVIEW_REQUIRED)
    def test_human_confirmation_requires_review(self):
        self.assertEqual(assess_action(mandate(human_confirmation_required=True), proposal(), NOW).decision, ActionDecision.REVIEW_REQUIRED)
    def test_naive_timestamp_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_action(mandate(), proposal(proposed_at="2026-10-30T12:00:00"), NOW)
    def test_future_proposal_timestamp_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_action(mandate(), proposal(proposed_at="2026-10-30T12:01:00+00:00"), NOW)
    def test_evidence_fingerprint_is_deterministic(self):
        a, b = assess_action(mandate(), proposal(), NOW), assess_action(mandate(), proposal(), NOW)
        self.assertEqual(a.evidence_fingerprint, b.evidence_fingerprint)
        self.assertEqual(a.assessment_id, b.assessment_id)
    def test_policy_version_change_changes_evidence(self):
        a = assess_action(mandate(), proposal(), NOW)
        b = assess_action(mandate(policy_version="policy-8"), proposal(), NOW)
        self.assertNotEqual(a.evidence_fingerprint, b.evidence_fingerprint)

if __name__ == "__main__":
    unittest.main()
