from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from mrinsight.analysis import (
    AnalysisEvidenceValidator,
    AnalysisGenerationStatus,
    FakeLLMProvider,
    GeneratePaperAnalysisService,
    LLMProvider,
    ScientificPaperAnalysis,
)
from mrinsight.analysis.schema import InformationStatus
from mrinsight.core.logging import log_event
from mrinsight.evaluation.fixtures import (
    GoldenEvaluationCase,
    load_golden_evaluation_cases,
)


@dataclass(frozen=True, slots=True)
class EvaluationCaseResult:
    """Machine-readable outcome for one evaluation case."""

    case_id: str
    description: str
    provider: str
    model: str
    status: str
    passed: bool
    expected_success: bool
    expected_repair_count: int
    repair_attempt_count: int
    schema_valid: bool
    evidence_coverage: float
    numerical_attribution_valid: bool
    scope_correct: bool
    unsupported_claim_errors: tuple[str, ...]
    validation_errors: tuple[str, ...]
    input_tokens: int | None
    output_tokens: int | None
    latency_ms: int | None
    estimated_cost_usd: float | None


@dataclass(frozen=True, slots=True)
class EvaluationSummary:
    """Aggregate quality and provider metrics."""

    total_cases: int
    passed_cases: int
    failed_cases: int
    pass_rate: float
    schema_validity_rate: float
    evidence_coverage_rate: float
    numerical_attribution_rate: float
    scope_correctness_rate: float
    repair_rate: float
    validation_failure_rate: float
    total_input_tokens: int
    total_output_tokens: int
    total_estimated_cost_usd: float
    average_latency_ms: float | None


@dataclass(frozen=True, slots=True)
class EvaluationReport:
    """Complete evaluation report."""

    generated_at: str
    provider_mode: str
    live_model_warning: str | None
    summary: EvaluationSummary
    cases: tuple[EvaluationCaseResult, ...]

    def to_json(
        self,
    ) -> str:
        """Return stable JSON for command output and CI artifacts."""

        return json.dumps(asdict(self), indent=2, sort_keys=True)


def run_evaluation(
    *,
    provider_mode: str = "fake",
    model_identifier: str = "fake-analysis-model-v1",
    provider_factory: Callable[[GoldenEvaluationCase], LLMProvider] | None = None,
    output_path: Path | None = None,
) -> EvaluationReport:
    """Run the golden evaluation set and optionally write a JSON report."""

    cases = load_golden_evaluation_cases()
    results = tuple(
        _run_case(
            case,
            provider_mode=provider_mode,
            model_identifier=model_identifier,
            provider_factory=provider_factory,
        )
        for case in cases
    )
    report = EvaluationReport(
        generated_at=datetime.now(UTC).isoformat(),
        provider_mode=provider_mode,
        live_model_warning=(
            "Configured-provider evaluation may call a live LLM, cost money, "
            "and vary over time."
            if provider_mode == "configured"
            else None
        ),
        summary=_summarize(results),
        cases=results,
    )

    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(report.to_json() + "\n", encoding="utf-8")

    log_event(
        "llm_evaluation_completed",
        provider_mode=provider_mode,
        total_cases=report.summary.total_cases,
        passed_cases=report.summary.passed_cases,
        pass_rate=report.summary.pass_rate,
        repair_rate=report.summary.repair_rate,
        validation_failure_rate=report.summary.validation_failure_rate,
    )

    return report


def _run_case(
    case: GoldenEvaluationCase,
    *,
    provider_mode: str,
    model_identifier: str,
    provider_factory: Callable[[GoldenEvaluationCase], LLMProvider] | None,
) -> EvaluationCaseResult:
    provider = (
        provider_factory(case)
        if provider_factory is not None
        else FakeLLMProvider(mode=case.fake_mode, model_identifier=model_identifier)
    )
    service = GeneratePaperAnalysisService(
        provider=provider,
        validator=AnalysisEvidenceValidator(),
        model_identifier=model_identifier,
    )
    result = service.execute(
        paper=case.paper,
        content=case.content,
        analysis_scope=case.analysis_scope,
        chunks=case.chunks,
    )
    response = result.final_provider_response
    schema_valid = result.analysis is not None
    evidence_coverage = (
        _evidence_coverage(result.analysis) if result.analysis is not None else 0.0
    )
    numerical_valid = not any(
        "numerical_results" in error and "value is not present" in error
        for error in result.validation_errors
    )
    scope_correct = not any(
        "abstract content cannot be presented as full-text analysis" in error
        for error in result.validation_errors
    )
    expected_status_met = (
        result.status
        in {
            AnalysisGenerationStatus.VALID,
            AnalysisGenerationStatus.REPAIRED,
        }
    ) == case.expected_success
    expected_repair_met = result.repair_attempt_count == case.expected_repair_count
    passed = expected_status_met and expected_repair_met

    return EvaluationCaseResult(
        case_id=case.case_id,
        description=case.description,
        provider=provider.name,
        model=model_identifier,
        status=result.status.value,
        passed=passed,
        expected_success=case.expected_success,
        expected_repair_count=case.expected_repair_count,
        repair_attempt_count=result.repair_attempt_count,
        schema_valid=schema_valid,
        evidence_coverage=evidence_coverage,
        numerical_attribution_valid=numerical_valid,
        scope_correct=scope_correct,
        unsupported_claim_errors=tuple(
            error
            for error in result.validation_errors
            if "require evidence" in error
            or "unknown chunk_id" in error
            or "excerpt does not occur" in error
        ),
        validation_errors=result.validation_errors,
        input_tokens=response.input_tokens if response is not None else None,
        output_tokens=response.output_tokens if response is not None else None,
        latency_ms=response.latency_ms if response is not None else None,
        estimated_cost_usd=0.0 if provider_mode == "fake" else None,
    )


def _evidence_coverage(
    analysis: ScientificPaperAnalysis,
) -> float:
    payload = analysis.model_dump(mode="json")
    claim_count = 0
    covered_count = 0

    def visit(value: object) -> None:
        nonlocal claim_count, covered_count

        if isinstance(value, dict):
            if "status" in value and "evidence_references" in value:
                status = value.get("status")
                if status in {
                    InformationStatus.REPORTED.value,
                    InformationStatus.UNCERTAIN.value,
                }:
                    claim_count += 1
                    references = value.get("evidence_references")
                    if isinstance(references, list) and references:
                        covered_count += 1
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(payload)

    if claim_count == 0:
        return 1.0
    return covered_count / claim_count


def _summarize(
    results: tuple[EvaluationCaseResult, ...],
) -> EvaluationSummary:
    total_cases = len(results)
    passed_cases = sum(1 for result in results if result.passed)
    latencies = [
        result.latency_ms for result in results if result.latency_ms is not None
    ]

    return EvaluationSummary(
        total_cases=total_cases,
        passed_cases=passed_cases,
        failed_cases=total_cases - passed_cases,
        pass_rate=_rate(passed_cases, total_cases),
        schema_validity_rate=_rate(
            sum(1 for result in results if result.schema_valid),
            total_cases,
        ),
        evidence_coverage_rate=(
            sum(result.evidence_coverage for result in results) / total_cases
            if total_cases
            else 0.0
        ),
        numerical_attribution_rate=_rate(
            sum(1 for result in results if result.numerical_attribution_valid),
            total_cases,
        ),
        scope_correctness_rate=_rate(
            sum(1 for result in results if result.scope_correct),
            total_cases,
        ),
        repair_rate=_rate(
            sum(1 for result in results if result.repair_attempt_count > 0),
            total_cases,
        ),
        validation_failure_rate=_rate(
            sum(1 for result in results if result.validation_errors),
            total_cases,
        ),
        total_input_tokens=sum(result.input_tokens or 0 for result in results),
        total_output_tokens=sum(result.output_tokens or 0 for result in results),
        total_estimated_cost_usd=sum(
            result.estimated_cost_usd or 0.0 for result in results
        ),
        average_latency_ms=(sum(latencies) / len(latencies) if latencies else None),
    )


def _rate(
    numerator: int,
    denominator: int,
) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator
