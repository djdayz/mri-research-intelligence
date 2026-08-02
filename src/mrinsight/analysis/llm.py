from __future__ import annotations

import json
import time
from dataclasses import dataclass
from enum import StrEnum
from importlib import import_module
from typing import Any, Protocol, cast
from uuid import uuid4

from mrinsight.analysis.schema import (
    ANALYSIS_SCHEMA_VERSION,
    EvidenceBackedText,
    EvidenceReference,
    EvidenceRole,
    InformationStatus,
    NumericalResult,
    ResultDirection,
    ScientificPaperAnalysis,
    build_unavailable_statement,
)
from mrinsight.papers import AnalysisScope, SectionType


class LLMProviderError(RuntimeError):
    """Base provider-independent LLM error."""


class LLMProviderTimeoutError(LLMProviderError):
    """Raised when an LLM provider exceeds the configured timeout."""


class LLMProviderUnavailableError(LLMProviderError):
    """Raised when an LLM provider fails before producing a response."""


class UnconfiguredLLMProvider:
    """LLM provider that fails clearly when credentials are absent."""

    @property
    def name(self) -> str:
        """Return the provider name."""

        return "unconfigured"

    def complete(
        self,
        request: LLMRequest,
    ) -> LLMResponse:
        """Fail because no live LLM provider is configured."""

        del request

        raise LLMProviderUnavailableError(
            "No LLM provider is configured. Set MRINSIGHT_LLM_PROVIDER and "
            "MRINSIGHT_LLM_API_KEY for live analysis."
        )


@dataclass(frozen=True, slots=True)
class LLMEvidenceChunk:
    """Evidence chunk supplied to an LLM provider."""

    chunk_id: int
    paper_id: int
    content_id: int
    section: SectionType
    text: str
    start_char: int
    end_char: int
    start_page: int | None
    end_page: int | None


@dataclass(frozen=True, slots=True)
class LLMRequest:
    """Provider-independent LLM request."""

    paper_id: int
    content_id: int
    analysis_scope: AnalysisScope
    source_checksum: str
    schema_version: str
    prompt_version: str
    prompt_checksum: str
    model_identifier: str
    system_prompt: str
    user_prompt: str
    input_checksum: str
    chunks: tuple[LLMEvidenceChunk, ...]
    repair_errors: tuple[str, ...] = ()
    previous_response: str | None = None


@dataclass(frozen=True, slots=True)
class LLMResponse:
    """Provider-independent LLM response."""

    provider_name: str
    model_identifier: str
    raw_text: str
    provider_request_id: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    latency_ms: int | None = None


class LLMProvider(Protocol):
    """Provider protocol for scientific analysis generation."""

    @property
    def name(self) -> str:
        """Return the provider name."""

    def complete(
        self,
        request: LLMRequest,
    ) -> LLMResponse:
        """Return one raw model response."""


class FakeLLMMode(StrEnum):
    """Deterministic fake LLM behaviours for offline tests."""

    VALID = "valid"
    MALFORMED_JSON = "malformed_json"
    SCHEMA_INVALID = "schema_invalid"
    MISSING_EVIDENCE = "missing_evidence"
    INVALID_CHUNK_REFERENCE = "invalid_chunk_reference"
    ABSTRACT_FULL_TEXT_MISMATCH = "abstract_full_text_mismatch"
    NUMERICAL_INCONSISTENCY = "numerical_inconsistency"
    TIMEOUT = "timeout"
    FAILURE = "failure"
    REPAIRABLE_MALFORMED_JSON = "repairable_malformed_json"


class FakeLLMProvider:
    """Deterministic fake LLM provider for contract and repair tests."""

    def __init__(
        self,
        *,
        mode: FakeLLMMode = FakeLLMMode.VALID,
        model_identifier: str = "fake-analysis-model-v1",
    ) -> None:
        self._mode = mode
        self._model_identifier = model_identifier
        self._call_count = 0

    @property
    def name(self) -> str:
        """Return the provider name."""

        return "fake"

    @property
    def call_count(self) -> int:
        """Return how many completion calls were made."""

        return self._call_count

    def complete(
        self,
        request: LLMRequest,
    ) -> LLMResponse:
        """Return deterministic fake output for the configured mode."""

        self._call_count += 1

        if self._mode is FakeLLMMode.TIMEOUT:
            raise LLMProviderTimeoutError("fake provider timeout")

        if self._mode is FakeLLMMode.FAILURE:
            raise LLMProviderUnavailableError("fake provider failure")

        should_emit_malformed_json = (
            self._mode is FakeLLMMode.REPAIRABLE_MALFORMED_JSON
            and self._call_count == 1
            or self._mode is FakeLLMMode.MALFORMED_JSON
        )

        if should_emit_malformed_json:
            raw_text = '{"schema_version":'
        else:
            raw_text = self._build_response_json(request)

        return LLMResponse(
            provider_name=self.name,
            model_identifier=self._model_identifier,
            raw_text=raw_text,
            provider_request_id=f"fake-{uuid4()}",
            input_tokens=len(request.user_prompt.split()),
            output_tokens=len(raw_text.split()),
            latency_ms=1,
        )

    def _build_response_json(
        self,
        request: LLMRequest,
    ) -> str:
        """Build deterministic JSON for the fake response."""

        chunk = request.chunks[0]
        reference = EvidenceReference(
            paper_id=chunk.paper_id,
            content_id=chunk.content_id,
            chunk_id=chunk.chunk_id,
            section=chunk.section,
            start_page=chunk.start_page,
            end_page=chunk.end_page,
            start_char=chunk.start_char,
            end_char=chunk.end_char,
            excerpt=chunk.text[:80],
            role=EvidenceRole.PRIMARY,
        )
        numerical_reference = reference.model_copy(
            update={"role": EvidenceRole.NUMERICAL}
        )

        if self._mode is FakeLLMMode.SCHEMA_INVALID:
            return json.dumps({"schema_version": ANALYSIS_SCHEMA_VERSION})

        objective = EvidenceBackedText(
            status=InformationStatus.REPORTED,
            text="The paper studies MRI evidence using supplied chunks.",
            evidence_references=(reference,),
        )

        if self._mode is FakeLLMMode.INVALID_CHUNK_REFERENCE:
            bad_reference = reference.model_copy(update={"chunk_id": 999999})
            objective = objective.model_copy(
                update={"evidence_references": (bad_reference,)}
            )

        analysis_scope = request.analysis_scope
        if self._mode is FakeLLMMode.ABSTRACT_FULL_TEXT_MISMATCH:
            analysis_scope = AnalysisScope.FULL_TEXT

        numerical_value_text = "2.5"
        if self._mode is FakeLLMMode.NUMERICAL_INCONSISTENCY:
            numerical_value_text = "9999"

        unavailable = build_unavailable_statement("Not reported in supplied evidence.")
        abstract_limited = build_unavailable_statement(
            "Unavailable because only abstract evidence was supplied.",
            status=InformationStatus.UNAVAILABLE_ABSTRACT_ONLY,
        )

        analysis = ScientificPaperAnalysis(
            schema_version=ANALYSIS_SCHEMA_VERSION,
            paper_id=request.paper_id,
            analysis_scope=analysis_scope,
            content_id=request.content_id,
            source_checksum=request.source_checksum,
            objective=objective,
            study_design=unavailable,
            population_or_dataset=unavailable,
            acquisition_details=(
                abstract_limited
                if request.analysis_scope is AnalysisScope.ABSTRACT_ONLY
                else unavailable
            ),
            preprocessing=unavailable,
            methodology_steps=(objective,),
            model_or_statistical_methods=unavailable,
            validation_design=unavailable,
            comparison_methods=unavailable,
            key_results=(objective,),
            numerical_results=(
                NumericalResult(
                    metric="reported value",
                    value_text=numerical_value_text,
                    direction=ResultDirection.UNCERTAIN,
                    evidence_reference=numerical_reference,
                ),
            ),
            strengths=(unavailable,),
            limitations=(unavailable,),
            suggested_improvements=(unavailable,),
            reproducibility_notes=(unavailable,),
            clinical_or_scientific_significance=objective,
            uncertainty=(unavailable,),
            missing_information=(unavailable,),
        )

        payload = analysis.model_dump(mode="json")

        if self._mode is FakeLLMMode.MISSING_EVIDENCE:
            payload["objective"]["evidence_references"] = []

        return json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
        )


class OpenAIResponsesLLMProvider:
    """OpenAI Responses API adapter using structured Pydantic output."""

    def __init__(
        self,
        *,
        api_key: str,
        model_identifier: str,
        timeout_seconds: float,
        max_retries: int,
        client: Any | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("api_key must be provided for OpenAI LLM provider.")

        self._model_identifier = model_identifier
        self._client = client or _build_openai_client(
            api_key=api_key,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
        )

    @property
    def name(self) -> str:
        """Return the provider name."""

        return "openai"

    def complete(
        self,
        request: LLMRequest,
    ) -> LLMResponse:
        """Call the OpenAI Responses API and return raw JSON text."""

        started = time.perf_counter()

        try:
            response = self._client.responses.parse(
                model=self._model_identifier,
                input=[
                    {
                        "role": "system",
                        "content": request.system_prompt,
                    },
                    {
                        "role": "user",
                        "content": request.user_prompt,
                    },
                ],
                text_format=ScientificPaperAnalysis,
            )
        except TimeoutError as error:
            raise LLMProviderTimeoutError("OpenAI provider timed out.") from error
        except Exception as error:
            if error.__class__.__name__ in {
                "APITimeoutError",
                "TimeoutException",
            }:
                raise LLMProviderTimeoutError("OpenAI provider timed out.") from error
            raise LLMProviderUnavailableError(
                f"OpenAI provider failed: {error.__class__.__name__}"
            ) from error

        latency_ms = round((time.perf_counter() - started) * 1000)
        raw_text = _extract_openai_raw_text(response)
        usage = getattr(response, "usage", None)

        return LLMResponse(
            provider_name=self.name,
            model_identifier=self._model_identifier,
            raw_text=raw_text,
            provider_request_id=cast(str | None, getattr(response, "id", None)),
            input_tokens=cast(int | None, getattr(usage, "input_tokens", None)),
            output_tokens=cast(int | None, getattr(usage, "output_tokens", None)),
            latency_ms=latency_ms,
        )


def _build_openai_client(
    *,
    api_key: str,
    timeout_seconds: float,
    max_retries: int,
) -> Any:
    """Build the official OpenAI SDK client lazily."""

    openai_module = import_module("openai")
    return openai_module.OpenAI(
        api_key=api_key,
        timeout=timeout_seconds,
        max_retries=max_retries,
    )


def _extract_openai_raw_text(
    response: Any,
) -> str:
    """Extract JSON text from an OpenAI structured response."""

    parsed = getattr(response, "output_parsed", None)
    if isinstance(parsed, ScientificPaperAnalysis):
        return parsed.model_dump_json()

    output_text = getattr(response, "output_text", None)
    if isinstance(output_text, str) and output_text:
        return output_text

    raise LLMProviderUnavailableError("OpenAI response did not contain output text.")
