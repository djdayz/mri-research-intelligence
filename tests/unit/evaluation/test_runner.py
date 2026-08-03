import json
from pathlib import Path

from mrinsight.evaluation import run_evaluation


def test_fake_golden_evaluation_report_passes_expected_behaviors(
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "evaluation-report.json"

    report = run_evaluation(output_path=output_path)
    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert report.summary.total_cases == 5
    assert report.summary.failed_cases == 0
    assert report.summary.pass_rate == 1.0
    assert report.summary.repair_rate == 0.8
    assert report.summary.validation_failure_rate == 0.8
    assert report.summary.total_input_tokens > 0
    assert report.summary.total_output_tokens > 0
    assert report.summary.total_estimated_cost_usd == 0.0
    assert payload["summary"]["failed_cases"] == 0
    assert payload["provider_mode"] == "fake"
    assert payload["live_model_warning"] is None


def test_golden_evaluation_records_safety_failures_as_expected_passes() -> None:
    report = run_evaluation()
    cases = {case.case_id: case for case in report.cases}

    missing_evidence = cases["synthetic-missing-evidence"]
    numerical_mismatch = cases["synthetic-numerical-mismatch"]
    scope_mismatch = cases["synthetic-abstract-scope-mismatch"]

    assert missing_evidence.passed is True
    assert missing_evidence.expected_success is False
    assert missing_evidence.unsupported_claim_errors
    assert numerical_mismatch.numerical_attribution_valid is False
    assert scope_mismatch.scope_correct is False
