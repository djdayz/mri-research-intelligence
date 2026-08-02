from __future__ import annotations

import json
from dataclasses import dataclass
from enum import StrEnum

from pydantic import ValidationError

from mrinsight.analysis.llm import (
    LLMEvidenceChunk,
    LLMProvider,
    LLMProviderError,
    LLMRequest,
    LLMResponse,
)
from mrinsight.analysis.prompting import (
    build_analysis_user_prompt,
    build_repair_user_prompt,
    load_analysis_prompt,
    load_repair_prompt,
)
from mrinsight.analysis.schema import (
    ANALYSIS_SCHEMA_VERSION,
    ScientificPaperAnalysis,
)
from mrinsight.analysis.validation import (
    AnalysisEvidenceValidator,
)
from mrinsight.papers import AnalysisScope, StoredPaperChunk
from mrinsight.papers.content_records import StoredPaperContent
from mrinsight.papers.records import StoredPaper


class AnalysisGenerationStatus(StrEnum):
    """Final status of an LLM analysis-generation attempt."""

    VALID = "valid"
    REPAIRED = "repaired"
    INVALID = "invalid"
    PROVIDER_FAILED = "provider_failed"
    INELIGIBLE = "ineligible"


@dataclass(frozen=True, slots=True)
class AnalysisGenerationResult:
    """Result of validating an LLM-generated analysis."""

    status: AnalysisGenerationStatus
    analysis: ScientificPaperAnalysis | None
    validation_errors: tuple[str, ...]
    repair_attempt_count: int
    raw_provider_response: str | None
    final_provider_response: LLMResponse | None


class GeneratePaperAnalysisService:
    """Generate, validate, and optionally repair one paper analysis."""

    def __init__(
        self,
        *,
        provider: LLMProvider,
        validator: AnalysisEvidenceValidator,
        model_identifier: str,
    ) -> None:
        self._provider = provider
        self._validator = validator
        self._model_identifier = model_identifier

    def execute(
        self,
        *,
        paper: StoredPaper,
        content: StoredPaperContent,
        analysis_scope: AnalysisScope,
        chunks: tuple[StoredPaperChunk, ...],
    ) -> AnalysisGenerationResult:
        """Generate an analysis and validate it against persisted evidence."""

        if content.checksum is None or content.extracted_text is None:
            return AnalysisGenerationResult(
                status=AnalysisGenerationStatus.INELIGIBLE,
                analysis=None,
                validation_errors=("Content is not analyzable.",),
                repair_attempt_count=0,
                raw_provider_response=None,
                final_provider_response=None,
            )

        if not chunks:
            return AnalysisGenerationResult(
                status=AnalysisGenerationStatus.INELIGIBLE,
                analysis=None,
                validation_errors=("No evidence chunks are available.",),
                repair_attempt_count=0,
                raw_provider_response=None,
                final_provider_response=None,
            )

        request = self.build_request(
            paper=paper,
            content=content,
            analysis_scope=analysis_scope,
            chunks=chunks,
        )

        try:
            first_response = self._provider.complete(request)
        except LLMProviderError as error:
            return AnalysisGenerationResult(
                status=AnalysisGenerationStatus.PROVIDER_FAILED,
                analysis=None,
                validation_errors=(str(error),),
                repair_attempt_count=0,
                raw_provider_response=None,
                final_provider_response=None,
            )

        analysis, validation_errors = self._validate_response(
            response=first_response,
            paper=paper,
            content=content,
            chunks=chunks,
        )

        if analysis is not None:
            return AnalysisGenerationResult(
                status=AnalysisGenerationStatus.VALID,
                analysis=analysis,
                validation_errors=(),
                repair_attempt_count=0,
                raw_provider_response=first_response.raw_text,
                final_provider_response=first_response,
            )

        repair_request = self._build_repair_request(
            original_request=request,
            previous_response=first_response,
            validation_errors=validation_errors,
        )

        try:
            repair_response = self._provider.complete(repair_request)
        except LLMProviderError as error:
            return AnalysisGenerationResult(
                status=AnalysisGenerationStatus.PROVIDER_FAILED,
                analysis=None,
                validation_errors=validation_errors + (str(error),),
                repair_attempt_count=1,
                raw_provider_response=first_response.raw_text,
                final_provider_response=None,
            )

        repaired_analysis, repair_errors = self._validate_response(
            response=repair_response,
            paper=paper,
            content=content,
            chunks=chunks,
        )

        if repaired_analysis is not None:
            return AnalysisGenerationResult(
                status=AnalysisGenerationStatus.REPAIRED,
                analysis=repaired_analysis,
                validation_errors=validation_errors,
                repair_attempt_count=1,
                raw_provider_response=first_response.raw_text,
                final_provider_response=repair_response,
            )

        return AnalysisGenerationResult(
            status=AnalysisGenerationStatus.INVALID,
            analysis=None,
            validation_errors=validation_errors + repair_errors,
            repair_attempt_count=1,
            raw_provider_response=first_response.raw_text,
            final_provider_response=repair_response,
        )

    def build_request(
        self,
        *,
        paper: StoredPaper,
        content: StoredPaperContent,
        analysis_scope: AnalysisScope,
        chunks: tuple[StoredPaperChunk, ...],
    ) -> LLMRequest:
        """Build reproducible first-pass LLM request metadata."""

        prompt = load_analysis_prompt()
        llm_chunks = tuple(_to_llm_chunk(chunk) for chunk in chunks)
        user_prompt, input_checksum = build_analysis_user_prompt(
            paper_id=paper.id,
            content_id=content.id,
            analysis_scope=analysis_scope,
            source_checksum=content.checksum or "",
            chunks=llm_chunks,
        )

        return LLMRequest(
            paper_id=paper.id,
            content_id=content.id,
            analysis_scope=analysis_scope,
            source_checksum=content.checksum or "",
            schema_version=ANALYSIS_SCHEMA_VERSION,
            prompt_version=prompt.version,
            prompt_checksum=prompt.checksum,
            model_identifier=self._model_identifier,
            system_prompt=prompt.text,
            user_prompt=user_prompt,
            input_checksum=input_checksum,
            chunks=llm_chunks,
        )

    def _build_repair_request(
        self,
        *,
        original_request: LLMRequest,
        previous_response: LLMResponse,
        validation_errors: tuple[str, ...],
    ) -> LLMRequest:
        """Build the bounded single repair request."""

        prompt = load_repair_prompt()
        user_prompt, input_checksum = build_repair_user_prompt(
            original_user_prompt=original_request.user_prompt,
            previous_response=previous_response.raw_text,
            validation_errors=validation_errors,
        )

        return LLMRequest(
            paper_id=original_request.paper_id,
            content_id=original_request.content_id,
            analysis_scope=original_request.analysis_scope,
            source_checksum=original_request.source_checksum,
            schema_version=original_request.schema_version,
            prompt_version=prompt.version,
            prompt_checksum=prompt.checksum,
            model_identifier=original_request.model_identifier,
            system_prompt=prompt.text,
            user_prompt=user_prompt,
            input_checksum=input_checksum,
            chunks=original_request.chunks,
            repair_errors=validation_errors,
            previous_response=previous_response.raw_text,
        )

    def _validate_response(
        self,
        *,
        response: LLMResponse,
        paper: StoredPaper,
        content: StoredPaperContent,
        chunks: tuple[StoredPaperChunk, ...],
    ) -> tuple[ScientificPaperAnalysis | None, tuple[str, ...]]:
        """Validate raw JSON, schema, evidence, and numerical attribution."""

        try:
            json.loads(response.raw_text)
        except json.JSONDecodeError as error:
            return None, (f"Malformed JSON: {error.msg}",)

        try:
            analysis = ScientificPaperAnalysis.model_validate_json(response.raw_text)
        except ValidationError as error:
            return None, tuple(str(item) for item in error.errors())

        evidence_result = self._validator.validate(
            analysis=analysis,
            paper=paper,
            content=content,
            chunks=chunks,
        )

        if not evidence_result.valid:
            return None, evidence_result.errors

        return analysis, ()


def _to_llm_chunk(
    chunk: StoredPaperChunk,
) -> LLMEvidenceChunk:
    """Convert a persisted chunk into provider-independent LLM input."""

    return LLMEvidenceChunk(
        chunk_id=chunk.id,
        paper_id=chunk.paper_id,
        content_id=chunk.paper_content_id,
        section=chunk.section_type,
        text=chunk.text,
        start_char=chunk.start_char,
        end_char=chunk.end_char,
        start_page=chunk.page_number,
        end_page=chunk.end_page_number,
    )
