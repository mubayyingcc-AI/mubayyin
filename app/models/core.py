"""
Mubayyin core domain models.

These are deliberately plain dataclasses (no ORM) so the engine has zero
external dependencies and can be run, tested, and reasoned about without
any package installation. The FastAPI/SQLAlchemy layer in app/api wraps
these same objects for a real HTTP service.
"""
from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def _now() -> float:
    return time.time()


class Severity(str, Enum):
    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"
    NONE = "none"


class ReleaseStatus(str, Enum):
    SAFE_TO_SERVE = "safe_to_serve"
    CONDITIONAL_SERVE = "conditional_serve"
    HOLD_FOR_REPAIR = "hold_for_repair"


@dataclass
class AISystem:
    """The customer's AI application under test — identity + exact
    configuration snapshot. A Release Record always points at one of these."""
    system_id: str
    name: str
    organization: str
    jurisdiction: str            # e.g. "AE", "SA"
    model_provider: str
    model_version: str
    prompt_version: str
    retrieval_version: Optional[str] = None
    policy_version: str = "v1"
    tool_version: Optional[str] = None
    created_at: float = field(default_factory=_now)

    def config_hash(self) -> str:
        """Hash of the exact configuration under test — this is what makes
        a Release Record reproducible: 'what, exactly, was tested'."""
        payload = json.dumps(
            {
                "model_provider": self.model_provider,
                "model_version": self.model_version,
                "prompt_version": self.prompt_version,
                "retrieval_version": self.retrieval_version,
                "policy_version": self.policy_version,
                "tool_version": self.tool_version,
            },
            sort_keys=True,
        )
        return hashlib.sha256(payload.encode()).hexdigest()


@dataclass
class ScenarioCase:
    """One test case. Category/language/dialect are tracked explicitly so
    coverage can be reported honestly instead of collapsed into one score."""
    scenario_id: str
    language: str                # "ar" | "en" | "ar-en"
    dialect: Optional[str]        # "MSA" | "Saudi" | "Emirati" | None
    category: str                # e.g. "financial_disclosure", "escalation"
    risk_level: str               # "low" | "medium" | "high"
    user_input: str
    expected_behavior: str
    forbidden_behavior: Optional[str] = None
    requires_escalation: bool = False
    required_disclosure: Optional[str] = None
    sensitive_markers: list[str] = field(default_factory=list)
    source: str = "synthetic"     # "synthetic" | "customer_provided" | "production_failure"

    def config_hash(self) -> str:
        """Hash every scenario field that can change the meaning of a test."""
        payload = json.dumps({
            "scenario_id": self.scenario_id, "language": self.language,
            "dialect": self.dialect, "category": self.category,
            "risk_level": self.risk_level, "user_input": self.user_input,
            "expected_behavior": self.expected_behavior,
            "forbidden_behavior": self.forbidden_behavior,
            "requires_escalation": self.requires_escalation,
            "required_disclosure": self.required_disclosure, "sensitive_markers": sorted(self.sensitive_markers), "source": self.source,
        }, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass
class DeterministicCheckResult:
    passed: bool
    rule: str
    detail: str = ""


@dataclass
class JudgeScore:
    """Structured rubric from one LLM judge. Never a single opaque number."""
    judge_name: str
    groundedness: float
    policy_adherence: Optional[float]
    language_quality: Optional[float]
    escalation_quality: Optional[float]
    privacy_behavior: Optional[float]
    severity: Severity
    reason: str


@dataclass
class HumanReview:
    reviewer: str
    agrees_with_automation: bool
    override_severity: Optional[Severity] = None
    comment: str = ""
    reviewed_at: float = field(default_factory=_now)


@dataclass
class TrialResult:
    """The outcome of running one scenario against one AI system version."""
    result_id: str
    scenario_id: str
    system_config_hash: str
    model_output: str
    scenario_config_hash: str = ""
    deterministic_checks: list[DeterministicCheckResult] = field(default_factory=list)
    judge_scores: list[JudgeScore] = field(default_factory=list)
    human_review: Optional[HumanReview] = None
    final_severity: Severity = Severity.NONE

    def is_critical_failure(self) -> bool:
        if self.human_review and self.human_review.override_severity:
            return self.human_review.override_severity == Severity.CRITICAL
        return self.final_severity == Severity.CRITICAL

    def is_failure(self) -> bool:
        sev = self.final_severity
        if self.human_review and self.human_review.override_severity:
            sev = self.human_review.override_severity
        return sev in (Severity.CRITICAL, Severity.MAJOR)


@dataclass
class ReleaseRecord:
    """The core object of the whole product. Immutable once created —
    supersede with a new version rather than editing in place."""
    record_id: str
    system_id: str
    system_config_hash: str
    scenario_set_version: str
    total_scenarios: int
    critical_failures: int
    major_failures: int
    minor_failures: int
    status: ReleaseStatus
    conditions: list[str]
    reason_codes: list[str]
    approver: Optional[str]
    evidence_hash: str
    previous_record_hash: Optional[str]
    trial_result_ids: list[str] = field(default_factory=list)
    required_scenario_ids: list[str] = field(default_factory=list)
    missing_scenario_ids: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=_now)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["status"] = self.status.value
        return d
