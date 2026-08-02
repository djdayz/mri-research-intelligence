from types import SimpleNamespace

import pytest
from tests.unit.analysis.helpers import make_chunk, make_content, make_paper

from mrinsight.analysis import (
    AnalysisEvidenceValidator,
    FakeLLMMode,
    FakeLLMProvider,
    GeneratePaperAnalysisService,
    LLMProviderTimeoutError,
    LLMProviderUnavailableError,
    LLMRequest,
    OpenAIResponsesLLMProvider,
)
from mrinsight.analysis.schema import ScientificPaperAnalysis
from mrinsight.papers import AnalysisScope


class FakeResponsesClient:
    """Small test double for OpenAI's responses resource."""

    def __init__(
        self,
        response: object | None = None,
        error: Exception | None = None,
    ) -> None:
        self.response = response
        self.error = error
        self.last_kwargs: dict[str, object] | None = None

    def parse(
        self,
        **kwargs: object,
    ) -> object:
        self.last_kwargs = kwargs
        if self.error is not None:
            raise self.error
        return self.response


class FakeOpenAIClient:
    """Small test double for the official OpenAI client."""

    def __init__(
        self,
        responses: FakeResponsesClient,
    ) -> None:
        self.responses = responses


def make_request() -> LLMRequest:
    """Build a real provider-independent request for adapter tests."""

    service = GeneratePaperAnalysisService(
        provider=FakeLLMProvider(mode=FakeLLMMode.VALID),
        validator=AnalysisEvidenceValidator(),
        model_identifier="fake",
    )

    return service.build_request(
        paper=make_paper(),
        content=make_content(),
        analysis_scope=AnalysisScope.ABSTRACT_ONLY,
        chunks=(make_chunk(),),
    )


def make_valid_analysis() -> ScientificPaperAnalysis:
    """Return a valid structured analysis payload."""

    request = make_request()
    response = FakeLLMProvider(mode=FakeLLMMode.VALID).complete(request)

    return ScientificPaperAnalysis.model_validate_json(response.raw_text)


def test_openai_provider_extracts_structured_output_and_usage() -> None:
    parsed = make_valid_analysis()
    responses = FakeResponsesClient(
        SimpleNamespace(
            id="resp_123",
            output_parsed=parsed,
            usage=SimpleNamespace(
                input_tokens=42,
                output_tokens=84,
            ),
        )
    )
    provider = OpenAIResponsesLLMProvider(
        api_key="test-key",
        model_identifier="gpt-test",
        timeout_seconds=5.0,
        max_retries=1,
        client=FakeOpenAIClient(responses),
    )

    result = provider.complete(make_request())

    assert result.provider_name == "openai"
    assert result.model_identifier == "gpt-test"
    assert result.provider_request_id == "resp_123"
    assert result.input_tokens == 42
    assert result.output_tokens == 84
    assert ScientificPaperAnalysis.model_validate_json(result.raw_text) == parsed
    assert responses.last_kwargs is not None
    assert responses.last_kwargs["model"] == "gpt-test"
    assert responses.last_kwargs["text_format"] is ScientificPaperAnalysis


def test_openai_provider_uses_output_text_fallback() -> None:
    parsed = make_valid_analysis()
    responses = FakeResponsesClient(
        SimpleNamespace(
            id="resp_456",
            output_parsed=None,
            output_text=parsed.model_dump_json(),
            usage=None,
        )
    )
    provider = OpenAIResponsesLLMProvider(
        api_key="test-key",
        model_identifier="gpt-test",
        timeout_seconds=5.0,
        max_retries=1,
        client=FakeOpenAIClient(responses),
    )

    result = provider.complete(make_request())

    assert ScientificPaperAnalysis.model_validate_json(result.raw_text) == parsed


def test_openai_provider_maps_timeout() -> None:
    responses = FakeResponsesClient(error=TimeoutError("slow"))
    provider = OpenAIResponsesLLMProvider(
        api_key="test-key",
        model_identifier="gpt-test",
        timeout_seconds=5.0,
        max_retries=1,
        client=FakeOpenAIClient(responses),
    )

    with pytest.raises(LLMProviderTimeoutError):
        provider.complete(make_request())


def test_openai_provider_rejects_empty_structured_response() -> None:
    responses = FakeResponsesClient(SimpleNamespace(id="resp_789", usage=None))
    provider = OpenAIResponsesLLMProvider(
        api_key="test-key",
        model_identifier="gpt-test",
        timeout_seconds=5.0,
        max_retries=1,
        client=FakeOpenAIClient(responses),
    )

    with pytest.raises(LLMProviderUnavailableError):
        provider.complete(make_request())
