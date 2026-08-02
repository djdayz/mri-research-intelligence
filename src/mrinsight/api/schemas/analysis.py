from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from mrinsight.analysis.records import StoredPaperAnalysis
from mrinsight.application.services import AnalyzePaperResult


class PaperAnalysisResponse(BaseModel):
    """Public response for structured scientific paper analysis."""

    model_config = ConfigDict(extra="forbid")

    id: int
    paper_id: int
    paper_content_id: int
    analysis_scope: str
    content_checksum: str
    selected_evidence_checksum: str
    llm_run_id: int | None
    schema_version: str
    provider: str
    model: str
    prompt_version: str
    status: str
    cached: bool
    outcome: str | None
    validation_errors: tuple[str, ...]
    analysis: dict[str, Any] | None
    evidence_references: tuple[dict[str, Any], ...]
    relevance_version: str | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_result(
        cls,
        result: AnalyzePaperResult,
    ) -> "PaperAnalysisResponse":
        """Create an API response from an analysis generation result."""

        return cls.from_stored(
            result.analysis,
            cached=result.cached,
            outcome=result.outcome.value,
        )

    @classmethod
    def from_stored(
        cls,
        analysis: StoredPaperAnalysis,
        *,
        cached: bool = False,
        outcome: str | None = None,
    ) -> "PaperAnalysisResponse":
        """Create an API response from a stored analysis."""

        return cls(
            id=analysis.id,
            paper_id=analysis.paper_id,
            paper_content_id=analysis.paper_content_id,
            analysis_scope=analysis.analysis_scope.value,
            content_checksum=analysis.content_checksum,
            selected_evidence_checksum=analysis.selected_evidence_checksum,
            llm_run_id=analysis.llm_run_id,
            schema_version=analysis.schema_version,
            provider=analysis.provider,
            model=analysis.model,
            prompt_version=analysis.prompt_version,
            status=analysis.status.value,
            cached=cached or analysis.cached,
            outcome=outcome,
            validation_errors=analysis.validation_errors,
            analysis=analysis.validated_analysis,
            evidence_references=_collect_evidence_references(
                analysis.validated_analysis
            ),
            relevance_version=analysis.relevance_version,
            created_at=analysis.created_at,
            updated_at=analysis.updated_at,
        )


def _collect_evidence_references(
    payload: dict[str, Any] | None,
) -> tuple[dict[str, Any], ...]:
    """Return unique evidence references visible in the analysis JSON."""

    if payload is None:
        return ()

    references: list[dict[str, Any]] = []
    seen: set[tuple[int | None, str | None]] = set()

    def visit(
        value: Any,
    ) -> None:
        if isinstance(value, dict):
            maybe_reference = value.get("evidence_reference")
            if isinstance(maybe_reference, dict):
                append_reference(maybe_reference)

            maybe_references = value.get("evidence_references")
            if isinstance(maybe_references, list):
                for item in maybe_references:
                    if isinstance(item, dict):
                        append_reference(item)

            for nested in value.values():
                visit(nested)
        elif isinstance(value, list):
            for item in value:
                visit(item)

    def append_reference(
        reference: dict[str, Any],
    ) -> None:
        key = (
            reference.get("chunk_id")
            if isinstance(reference.get("chunk_id"), int)
            else None,
            reference.get("role") if isinstance(reference.get("role"), str) else None,
        )
        if key in seen:
            return
        seen.add(key)
        references.append(reference)

    visit(payload)

    return tuple(references)
