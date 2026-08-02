from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any

from mrinsight.papers import AnalysisScope


class LLMRunStatus(StrEnum):
    """Persisted status for one provider request sequence."""

    SUCCEEDED = "succeeded"
    FAILED = "failed"
    PROVIDER_FAILED = "provider_failed"


class PaperAnalysisStatus(StrEnum):
    """Persisted status for one paper analysis."""

    SUCCEEDED = "succeeded"
    FAILED = "failed"
    INELIGIBLE = "ineligible"


@dataclass(frozen=True, slots=True)
class NewLLMRun:
    """LLM run ready for persistence."""

    provider: str
    model: str
    prompt_version: str
    prompt_checksum: str
    schema_version: str
    input_checksum: str
    selected_chunk_ids: tuple[int, ...]
    request_status: LLMRunStatus
    repair_attempt_count: int
    provider_request_id: str | None = None
    input_token_count: int | None = None
    output_token_count: int | None = None
    latency_ms: int | None = None
    estimated_cost: float | None = None
    error_category: str | None = None
    completed_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class StoredLLMRun:
    """Persisted LLM run."""

    id: int
    provider: str
    model: str
    prompt_version: str
    prompt_checksum: str
    schema_version: str
    input_checksum: str
    selected_chunk_ids: tuple[int, ...]
    request_status: LLMRunStatus
    repair_attempt_count: int
    created_at: datetime
    provider_request_id: str | None = None
    input_token_count: int | None = None
    output_token_count: int | None = None
    latency_ms: int | None = None
    estimated_cost: float | None = None
    error_category: str | None = None
    completed_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class NewPaperAnalysis:
    """Paper analysis ready for persistence."""

    paper_id: int
    paper_content_id: int
    analysis_scope: AnalysisScope
    content_checksum: str
    selected_evidence_checksum: str
    llm_run_id: int | None
    schema_version: str
    provider: str
    model: str
    prompt_version: str
    validated_analysis: dict[str, Any] | None
    status: PaperAnalysisStatus
    validation_errors: tuple[str, ...]
    relevance_version: str | None = None


@dataclass(frozen=True, slots=True)
class StoredPaperAnalysis:
    """Persisted paper analysis."""

    id: int
    paper_id: int
    paper_content_id: int
    analysis_scope: AnalysisScope
    content_checksum: str
    selected_evidence_checksum: str
    llm_run_id: int | None
    schema_version: str
    provider: str
    model: str
    prompt_version: str
    validated_analysis: dict[str, Any] | None
    status: PaperAnalysisStatus
    validation_errors: tuple[str, ...]
    created_at: datetime
    updated_at: datetime
    relevance_version: str | None = None
    cached: bool = False
