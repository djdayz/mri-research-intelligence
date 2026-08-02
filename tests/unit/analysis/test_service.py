from tests.unit.analysis.helpers import make_chunk, make_content, make_paper

from mrinsight.analysis import (
    AnalysisEvidenceValidator,
    AnalysisGenerationResult,
    AnalysisGenerationStatus,
    FakeLLMMode,
    FakeLLMProvider,
    GeneratePaperAnalysisService,
)
from mrinsight.papers import AnalysisScope


def make_service(
    mode: FakeLLMMode,
) -> tuple[GeneratePaperAnalysisService, FakeLLMProvider]:
    """Create a generation service with a fake provider."""

    provider = FakeLLMProvider(mode=mode)
    service = GeneratePaperAnalysisService(
        provider=provider,
        validator=AnalysisEvidenceValidator(),
        model_identifier="fake-analysis-model-v1",
    )
    return service, provider


def run_service(
    mode: FakeLLMMode,
) -> tuple[AnalysisGenerationResult, FakeLLMProvider]:
    """Run the service with one paper, content, and chunk."""

    service, provider = make_service(mode)
    result = service.execute(
        paper=make_paper(),
        content=make_content(),
        analysis_scope=AnalysisScope.ABSTRACT_ONLY,
        chunks=(make_chunk(),),
    )
    return result, provider


def test_valid_first_response_succeeds() -> None:
    result, provider = run_service(FakeLLMMode.VALID)

    assert result.status is AnalysisGenerationStatus.VALID
    assert result.analysis is not None
    assert result.repair_attempt_count == 0
    assert provider.call_count == 1


def test_repairable_malformed_json_repairs_once() -> None:
    result, provider = run_service(FakeLLMMode.REPAIRABLE_MALFORMED_JSON)

    assert result.status is AnalysisGenerationStatus.REPAIRED
    assert result.analysis is not None
    assert result.repair_attempt_count == 1
    assert provider.call_count == 2
    assert result.validation_errors[0].startswith("Malformed JSON")


def test_irreparable_malformed_json_fails_after_one_repair() -> None:
    result, provider = run_service(FakeLLMMode.MALFORMED_JSON)

    assert result.status is AnalysisGenerationStatus.INVALID
    assert result.analysis is None
    assert result.repair_attempt_count == 1
    assert provider.call_count == 2


def test_invalid_chunk_reference_is_rejected() -> None:
    result, provider = run_service(FakeLLMMode.INVALID_CHUNK_REFERENCE)

    assert result.status is AnalysisGenerationStatus.INVALID
    assert result.repair_attempt_count == 1
    assert provider.call_count == 2
    assert any("unknown chunk_id" in error for error in result.validation_errors)


def test_missing_evidence_is_rejected() -> None:
    result, _provider = run_service(FakeLLMMode.MISSING_EVIDENCE)

    assert result.status is AnalysisGenerationStatus.INVALID
    assert any(
        "Reported or uncertain claims require evidence" in error
        for error in result.validation_errors
    )


def test_abstract_full_text_mismatch_is_rejected() -> None:
    result, _provider = run_service(FakeLLMMode.ABSTRACT_FULL_TEXT_MISMATCH)

    assert result.status is AnalysisGenerationStatus.INVALID
    assert any("abstract content" in error for error in result.validation_errors)


def test_numerical_inconsistency_is_rejected() -> None:
    result, _provider = run_service(FakeLLMMode.NUMERICAL_INCONSISTENCY)

    assert result.status is AnalysisGenerationStatus.INVALID
    assert any("value is not present" in error for error in result.validation_errors)


def test_provider_timeout_fails_honestly() -> None:
    result, provider = run_service(FakeLLMMode.TIMEOUT)

    assert result.status is AnalysisGenerationStatus.PROVIDER_FAILED
    assert result.analysis is None
    assert result.repair_attempt_count == 0
    assert provider.call_count == 1
