import json

from tests.unit.analysis.helpers import make_chunk, make_content, make_paper

from mrinsight.analysis import (
    AnalysisEvidenceValidator,
    AnalysisGenerationResult,
    AnalysisGenerationStatus,
    FakeLLMMode,
    FakeLLMProvider,
    GeneratePaperAnalysisService,
    LLMRequest,
    LLMResponse,
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


def test_live_style_excerpt_offsets_are_canonicalized() -> None:
    chunk = make_chunk()
    provider = OffsetOnlyLLMProvider()
    service = GeneratePaperAnalysisService(
        provider=provider,
        validator=AnalysisEvidenceValidator(),
        model_identifier="offset-only-model",
    )

    result = service.execute(
        paper=make_paper(),
        content=make_content(),
        analysis_scope=AnalysisScope.ABSTRACT_ONLY,
        chunks=(chunk,),
    )

    assert result.status is AnalysisGenerationStatus.VALID
    assert result.analysis is not None
    assert result.analysis.objective.evidence_references[0].start_char == (
        chunk.start_char
    )
    assert result.analysis.objective.evidence_references[0].end_char == chunk.end_char
    assert result.analysis.objective.evidence_references[0].excerpt == chunk.text


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


class OffsetOnlyLLMProvider:
    """Fake a live model that cites the right chunk but excerpt-level offsets."""

    def __init__(self) -> None:
        self._provider = FakeLLMProvider(mode=FakeLLMMode.VALID)

    @property
    def name(self) -> str:
        """Return the provider name."""

        return "offset-only"

    def complete(
        self,
        request: LLMRequest,
    ) -> LLMResponse:
        """Return valid analysis JSON with non-canonical evidence offsets."""

        response = self._provider.complete(request)
        payload = json.loads(response.raw_text)
        _rewrite_reference_offsets(payload)
        _rewrite_reference_excerpts(payload)

        return LLMResponse(
            provider_name=self.name,
            model_identifier="offset-only-model",
            raw_text=json.dumps(payload),
            provider_request_id=response.provider_request_id,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            latency_ms=response.latency_ms,
        )


def _rewrite_reference_offsets(
    value: object,
) -> None:
    """Recursively rewrite evidence references to excerpt-level offsets."""

    if isinstance(value, dict):
        if {"chunk_id", "start_char", "end_char"}.issubset(value):
            value["start_char"] = 4
            value["end_char"] = 15
        for child in value.values():
            _rewrite_reference_offsets(child)
    elif isinstance(value, list):
        for child in value:
            _rewrite_reference_offsets(child)


def _rewrite_reference_excerpts(
    value: object,
) -> None:
    """Recursively rewrite evidence excerpts to live-style paraphrases."""

    if isinstance(value, dict):
        if {"chunk_id", "excerpt"}.issubset(value):
            value["excerpt"] = "MRI methods described a reported value."
        for child in value.values():
            _rewrite_reference_excerpts(child)
    elif isinstance(value, list):
        for child in value:
            _rewrite_reference_excerpts(child)
