from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from time import perf_counter

from mrinsight.analysis import (
    ANALYSIS_SCHEMA_VERSION,
    EvidenceSelectionService,
    GeneratePaperAnalysisService,
)
from mrinsight.analysis.records import (
    LLMRunStatus,
    NewLLMRun,
    NewPaperAnalysis,
    PaperAnalysisStatus,
    StoredPaperAnalysis,
)
from mrinsight.analysis.repositories import (
    LLMRunRepository,
    PaperAnalysisRepository,
)
from mrinsight.analysis.service import AnalysisGenerationStatus
from mrinsight.application.services.ingest_full_text import PaperNotFoundError
from mrinsight.application.services.select_analysis_content import (
    NoAnalyzableContentError,
    SelectAnalysisContentService,
)
from mrinsight.core.logging import log_event
from mrinsight.papers.repositories import PaperChunkRepository, PaperRepository
from mrinsight.relevance import RELEVANCE_MODEL_VERSION, RELEVANCE_RULES_VERSION


class PaperAnalysisOutcome(StrEnum):
    """High-level outcome for one analysis request."""

    CREATED = "created"
    CACHED = "cached"
    FAILED = "failed"
    PROVIDER_FAILED = "provider_failed"
    INELIGIBLE = "ineligible"


@dataclass(frozen=True, slots=True)
class AnalyzePaperResult:
    """Application result for paper analysis generation."""

    analysis: StoredPaperAnalysis
    outcome: PaperAnalysisOutcome

    @property
    def cached(self) -> bool:
        """Return whether a persisted successful analysis was reused."""

        return self.outcome is PaperAnalysisOutcome.CACHED


@dataclass(frozen=True, slots=True)
class AnalyzePaperService:
    """Select evidence, run structured analysis, and persist provenance."""

    paper_repository: PaperRepository
    content_selector: SelectAnalysisContentService
    chunk_repository: PaperChunkRepository
    analysis_repository: PaperAnalysisRepository
    llm_run_repository: LLMRunRepository
    evidence_selector: EvidenceSelectionService
    generation_service: GeneratePaperAnalysisService
    provider_name: str
    model_identifier: str

    def execute(
        self,
        paper_id: int,
    ) -> AnalyzePaperResult:
        """Generate or retrieve the current structured paper analysis."""

        paper = self.paper_repository.get_by_id(paper_id)

        if paper is None:
            raise PaperNotFoundError(f"Paper {paper_id} does not exist.")

        selected_content = self.content_selector.execute(paper_id)
        content = selected_content.content

        if content.checksum is None or content.extracted_text is None:
            raise NoAnalyzableContentError(
                f"Paper {paper_id} has no successful extracted text."
            )

        chunks = self.chunk_repository.list_by_content(content.id)
        selected_evidence = self.evidence_selector.select(chunks)

        if selected_evidence.chunks:
            request = self.generation_service.build_request(
                paper=paper,
                content=content,
                analysis_scope=selected_content.scope,
                chunks=selected_evidence.chunks,
            )
            prompt_version = request.prompt_version
            prompt_checksum = request.prompt_checksum
            input_checksum = request.input_checksum
        else:
            prompt_version = "analysis-prompt-unavailable"
            prompt_checksum = content.checksum
            input_checksum = selected_evidence.selection_checksum

        cached = self.analysis_repository.get_current(
            paper_id=paper.id,
            paper_content_id=content.id,
            analysis_scope=selected_content.scope,
            content_checksum=content.checksum,
            selected_evidence_checksum=selected_evidence.selection_checksum,
            schema_version=ANALYSIS_SCHEMA_VERSION,
            provider=self.provider_name,
            model=self.model_identifier,
            prompt_version=prompt_version,
        )

        if cached is not None:
            return AnalyzePaperResult(
                analysis=cached,
                outcome=PaperAnalysisOutcome.CACHED,
            )

        generation_started_at = perf_counter()
        generation_result = self.generation_service.execute(
            paper=paper,
            content=content,
            analysis_scope=selected_content.scope,
            chunks=selected_evidence.chunks,
        )
        log_event(
            "llm_analysis_generation_completed",
            provider=self.provider_name,
            model=self.model_identifier,
            paper_id=paper.id,
            paper_content_id=content.id,
            analysis_scope=selected_content.scope.value,
            status=generation_result.status.value,
            repair_attempt_count=generation_result.repair_attempt_count,
            duration_ms=round((perf_counter() - generation_started_at) * 1000, 2),
        )
        run_status = _to_llm_run_status(generation_result.status)
        provider_response = generation_result.final_provider_response
        llm_run = None

        if generation_result.status is not AnalysisGenerationStatus.INELIGIBLE:
            llm_run = self.llm_run_repository.add(
                NewLLMRun(
                    provider=self.provider_name,
                    model=self.model_identifier,
                    prompt_version=prompt_version,
                    prompt_checksum=prompt_checksum,
                    schema_version=ANALYSIS_SCHEMA_VERSION,
                    input_checksum=input_checksum,
                    selected_chunk_ids=tuple(
                        chunk.id for chunk in selected_evidence.chunks
                    ),
                    request_status=run_status,
                    repair_attempt_count=generation_result.repair_attempt_count,
                    provider_request_id=(
                        provider_response.provider_request_id
                        if provider_response is not None
                        else None
                    ),
                    input_token_count=(
                        provider_response.input_tokens
                        if provider_response is not None
                        else None
                    ),
                    output_token_count=(
                        provider_response.output_tokens
                        if provider_response is not None
                        else None
                    ),
                    latency_ms=(
                        provider_response.latency_ms
                        if provider_response is not None
                        else None
                    ),
                    error_category=_error_category(generation_result.status),
                    completed_at=datetime.now(UTC),
                )
            )

        stored = self.analysis_repository.add(
            NewPaperAnalysis(
                paper_id=paper.id,
                paper_content_id=content.id,
                analysis_scope=selected_content.scope,
                content_checksum=content.checksum,
                selected_evidence_checksum=selected_evidence.selection_checksum,
                llm_run_id=llm_run.id if llm_run is not None else None,
                schema_version=ANALYSIS_SCHEMA_VERSION,
                provider=self.provider_name,
                model=self.model_identifier,
                prompt_version=prompt_version,
                validated_analysis=(
                    generation_result.analysis.model_dump(mode="json")
                    if generation_result.analysis is not None
                    else None
                ),
                status=_to_paper_analysis_status(generation_result.status),
                validation_errors=generation_result.validation_errors,
                relevance_version=(
                    f"{RELEVANCE_MODEL_VERSION}:{RELEVANCE_RULES_VERSION}"
                ),
            )
        )

        return AnalyzePaperResult(
            analysis=stored,
            outcome=_to_analysis_outcome(generation_result.status),
        )


def _to_llm_run_status(
    status: AnalysisGenerationStatus,
) -> LLMRunStatus:
    """Translate generation status into persisted LLM-run status."""

    if status in {
        AnalysisGenerationStatus.VALID,
        AnalysisGenerationStatus.REPAIRED,
    }:
        return LLMRunStatus.SUCCEEDED
    if status is AnalysisGenerationStatus.PROVIDER_FAILED:
        return LLMRunStatus.PROVIDER_FAILED
    return LLMRunStatus.FAILED


def _to_paper_analysis_status(
    status: AnalysisGenerationStatus,
) -> PaperAnalysisStatus:
    """Translate generation status into persisted paper-analysis status."""

    if status in {
        AnalysisGenerationStatus.VALID,
        AnalysisGenerationStatus.REPAIRED,
    }:
        return PaperAnalysisStatus.SUCCEEDED
    if status is AnalysisGenerationStatus.INELIGIBLE:
        return PaperAnalysisStatus.INELIGIBLE
    return PaperAnalysisStatus.FAILED


def _to_analysis_outcome(
    status: AnalysisGenerationStatus,
) -> PaperAnalysisOutcome:
    """Translate generation status into API-facing application outcome."""

    if status in {
        AnalysisGenerationStatus.VALID,
        AnalysisGenerationStatus.REPAIRED,
    }:
        return PaperAnalysisOutcome.CREATED
    if status is AnalysisGenerationStatus.PROVIDER_FAILED:
        return PaperAnalysisOutcome.PROVIDER_FAILED
    if status is AnalysisGenerationStatus.INELIGIBLE:
        return PaperAnalysisOutcome.INELIGIBLE
    return PaperAnalysisOutcome.FAILED


def _error_category(
    status: AnalysisGenerationStatus,
) -> str | None:
    """Return a compact non-secret error category for persistence."""

    if status is AnalysisGenerationStatus.PROVIDER_FAILED:
        return "provider_failed"
    if status is AnalysisGenerationStatus.INELIGIBLE:
        return "ineligible"
    if status is AnalysisGenerationStatus.INVALID:
        return "validation_failed"
    return None
