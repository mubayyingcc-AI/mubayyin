"""Mubayyin Action Mandate Assurance: deterministic assessment of a proposed action against a current, versioned mandate. This module does not execute or block actions."""
from __future__ import annotations
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from enum import Enum
import hashlib, json
from typing import Optional

class MandateState(str, Enum):
    ACTIVE = "active"
    REVOKED = "revoked"

class ActionDecision(str, Enum):
    PERMITTED = "permitted"
    REVIEW_REQUIRED = "review_required"
    REJECTED = "rejected"

@dataclass(frozen=True)
class ActionMandate:
    mandate_id: str
    mandate_version: str
    policy_version: str
    principal_id: str
    authorised_actor_id: str
    permitted_actions: tuple[str, ...]
    resource_id: str
    currency: str
    maximum_amount: str
    issued_at: str
    expires_at: str
    state: MandateState = MandateState.ACTIVE
    revoked_at: Optional[str] = None
    permitted_delegates: tuple[str, ...] = ()
    human_confirmation_required: bool = False

@dataclass(frozen=True)
class ProposedAction:
    request_id: str
    principal_id: str
    actor_id: str
    action_type: str
    resource_id: str
    currency: str
    amount: str
    proposed_at: str
    delegation_path: tuple[str, ...] = ()
    prior_execution_detected: bool = False
    context_complete: bool = True

@dataclass(frozen=True)
class ActionAssessment:
    assessment_id: str
    mandate_id: str
    mandate_version: str
    policy_version: str
    decision: ActionDecision
    reason_codes: tuple[str, ...]
    evaluated_at: str
    mandate_fingerprint: str
    proposal_fingerprint: str
    evidence_fingerprint: str
    engine_version: str = "mubayyin-action-mandate-assurance.v1"

    def to_dict(self) -> dict:
        value = asdict(self)
        value["decision"] = self.decision.value
        return value

def _digest(value: dict) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()

def _instant(value: str, field: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field} must include a timezone")
    return parsed.astimezone(timezone.utc)

def _money(value: str, field: str) -> Decimal:
    try:
        amount = Decimal(value)
    except (InvalidOperation, TypeError) as exc:
        raise ValueError(f"{field} must be a decimal amount") from exc
    if not amount.is_finite() or amount < 0:
        raise ValueError(f"{field} must be finite and non-negative")
    return amount

def assess_action(mandate: ActionMandate, proposal: ProposedAction, evaluated_at: Optional[str] = None) -> ActionAssessment:
    """Assess one proposed action against one mandate snapshot. Missing context never silently becomes permission."""
    at = evaluated_at or proposal.proposed_at
    now = _instant(at, "evaluated_at")
    issued = _instant(mandate.issued_at, "issued_at")
    expiry = _instant(mandate.expires_at, "expires_at")
    proposed = _instant(proposal.proposed_at, "proposed_at")
    if expiry <= issued:
        raise ValueError("expires_at must be later than issued_at")
    if proposed > now:
        raise ValueError("proposed_at cannot be later than evaluated_at")
    if mandate.revoked_at:
        _instant(mandate.revoked_at, "revoked_at")
    max_amount = _money(mandate.maximum_amount, "maximum_amount")
    amount = _money(proposal.amount, "amount")
    reasons: list[str] = []
    if mandate.state == MandateState.REVOKED:
        reasons.append("MANDATE_REVOKED")
    if mandate.revoked_at and _instant(mandate.revoked_at, "revoked_at") <= now:
        reasons.append("MANDATE_REVOKED")
    if now < issued or proposed < issued:
        reasons.append("MANDATE_NOT_YET_EFFECTIVE")
    if now >= expiry:
        reasons.append("MANDATE_EXPIRED")
    if proposal.principal_id != mandate.principal_id:
        reasons.append("PRINCIPAL_MISMATCH")
    if proposal.actor_id != mandate.authorised_actor_id and proposal.actor_id not in mandate.permitted_delegates:
        reasons.append("ACTOR_NOT_AUTHORISED")
    if proposal.action_type not in mandate.permitted_actions:
        reasons.append("ACTION_OUTSIDE_MANDATE")
    if proposal.resource_id != mandate.resource_id:
        reasons.append("RESOURCE_MISMATCH")
    if proposal.currency.upper() != mandate.currency.upper():
        reasons.append("CURRENCY_MISMATCH")
    if amount > max_amount:
        reasons.append("AMOUNT_EXCEEDS_LIMIT")
    if proposal.prior_execution_detected:
        reasons.append("POSSIBLE_DUPLICATE_EXECUTION")
    if proposal.delegation_path:
        if proposal.delegation_path[-1] != proposal.actor_id:
            reasons.append("DELEGATION_PATH_INCONSISTENT")
        if any(node not in mandate.permitted_delegates for node in proposal.delegation_path):
            reasons.append("DELEGATION_OUTSIDE_MANDATE")
    hard_failures = {
        "MANDATE_REVOKED", "MANDATE_EXPIRED", "MANDATE_NOT_YET_EFFECTIVE", "PRINCIPAL_MISMATCH", "ACTOR_NOT_AUTHORISED",
        "ACTION_OUTSIDE_MANDATE", "RESOURCE_MISMATCH", "CURRENCY_MISMATCH",
        "AMOUNT_EXCEEDS_LIMIT", "POSSIBLE_DUPLICATE_EXECUTION",
        "DELEGATION_PATH_INCONSISTENT", "DELEGATION_OUTSIDE_MANDATE",
    }
    if any(code in hard_failures for code in reasons):
        decision = ActionDecision.REJECTED
    elif not proposal.context_complete:
        reasons.append("ASSESSMENT_CONTEXT_INCOMPLETE")
        decision = ActionDecision.REVIEW_REQUIRED
    elif mandate.human_confirmation_required:
        reasons.append("HUMAN_CONFIRMATION_REQUIRED")
        decision = ActionDecision.REVIEW_REQUIRED
    else:
        reasons.append("MANDATE_CONDITIONS_SATISFIED")
        decision = ActionDecision.PERMITTED
    mandate_payload = asdict(mandate)
    mandate_payload["state"] = mandate.state.value
    proposal_payload = asdict(proposal)
    proposal_payload["delegation_path"] = list(proposal.delegation_path)
    mandate_hash = _digest(mandate_payload)
    proposal_hash = _digest(proposal_payload)
    evidence_payload = {
        "engine_version": "mubayyin-action-mandate-assurance.v1",
        "mandate_fingerprint": mandate_hash,
        "proposal_fingerprint": proposal_hash,
        "decision": decision.value,
        "reason_codes": sorted(set(reasons)),
        "evaluated_at": now.isoformat(),
    }
    evidence_hash = _digest(evidence_payload)
    return ActionAssessment(
        assessment_id="ama_" + evidence_hash[:24], mandate_id=mandate.mandate_id,
        mandate_version=mandate.mandate_version, policy_version=mandate.policy_version,
        decision=decision, reason_codes=tuple(sorted(set(reasons))),
        evaluated_at=now.isoformat(), mandate_fingerprint=mandate_hash,
        proposal_fingerprint=proposal_hash, evidence_fingerprint=evidence_hash,
    )
