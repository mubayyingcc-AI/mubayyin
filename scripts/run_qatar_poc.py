"""Run Mubayyin's synthetic Qatar bilingual financial-services PoC."""
from app.models.core import AISystem
from app.services.evaluator import run_trial
from app.services.release_gate import ReleaseThresholds, decide_release
from scenarios.qatar_financial_services_poc import BASELINE_OUTPUTS, REPAIRED_OUTPUTS, SCENARIOS


def run_set(system, outputs):
    results = []
    for scenario in SCENARIOS:
        result = run_trial(scenario, outputs[scenario.scenario_id])
        result.system_config_hash = system.config_hash()
        results.append(result)
    return results


def main():
    system = AISystem(
        system_id="qatar-financial-services-poc-v1",
        name="Synthetic Arabic-English financial services assistant",
        organization="Mubayyin PoC",
        jurisdiction="QA",
        model_provider="synthetic-fixture",
        model_version="fixture-v1",
        prompt_version="prompt-v1",
        policy_version="qatar-poc-synthetic-v1",
    )
    thresholds = ReleaseThresholds(max_critical_failures=0, max_major_failures=0)
    required = [scenario.scenario_id for scenario in SCENARIOS]

    baseline_trials = run_set(system, BASELINE_OUTPUTS)
    baseline = decide_release(
        system, baseline_trials, thresholds, approver=None,
        scenario_set_version="qa-financial-poc-v1",
        required_scenario_ids=required,
    )
    print("BASELINE")
    print(f"status={baseline.status.value}")
    print(f"critical={baseline.critical_failures} major={baseline.major_failures}")
    print(f"reason_codes={','.join(baseline.reason_codes)}")

    repaired_trials = run_set(system, REPAIRED_OUTPUTS)
    missing_coverage = decide_release(
        system, repaired_trials[:-1], thresholds, approver=None,
        scenario_set_version="qa-financial-poc-v1",
        required_scenario_ids=required,
    )
    print("COVERAGE GATE")
    print(f"status={missing_coverage.status.value}")
    print(f"missing={','.join(missing_coverage.missing_scenario_ids)}")

    repaired = decide_release(
        system, repaired_trials, thresholds, approver="Synthetic PoC reviewer",
        previous_record_hash=baseline.evidence_hash,
        scenario_set_version="qa-financial-poc-v1",
        required_scenario_ids=required,
    )
    deterministic_failures = sum(
        1 for result in repaired_trials for check in result.deterministic_checks if not check.passed
    )
    print("RETEST")
    print(f"status={repaired.status.value}")
    print(f"deterministic_failures={deterministic_failures}")
    print(f"critical={repaired.critical_failures} major={repaired.major_failures}")
    print(f"baseline_hash={baseline.evidence_hash}")
    print(f"retest_hash={repaired.evidence_hash}")
    print("NOTE: synthetic fixture only; lexical reference evaluation is not semantic Arabic validation or certification.")

    assert baseline.status.value == "hold_for_repair"
    assert missing_coverage.status.value == "hold_for_repair"
    assert not missing_coverage.missing_scenario_ids == []
    assert deterministic_failures == 0
    assert baseline.evidence_hash != repaired.evidence_hash


if __name__ == "__main__":
    main()
