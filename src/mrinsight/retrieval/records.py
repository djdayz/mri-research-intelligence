from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum
from typing import Any


class PaperSort(StrEnum):
    """Stable sorting modes for paper retrieval."""

    NEWEST_PUBLICATION = "newest_publication"
    OLDEST_PUBLICATION = "oldest_publication"
    NEWEST_INGESTION = "newest_ingestion"
    RELEVANCE_SCORE = "relevance_score"
    TITLE = "title"


@dataclass(frozen=True, slots=True)
class PaperSearchFilters:
    """Validated search filters for paper retrieval."""

    doi: str | None = None
    title_query: str | None = None
    publication_date_from: date | None = None
    publication_date_to: date | None = None
    journal: str | None = None
    ingestion_source: str | None = None
    content_scope: str | None = None
    extraction_status: str | None = None
    relevance_label: str | None = None
    mri_category: str | None = None
    analysis_status: str | None = None
    analysis_scope: str | None = None


@dataclass(frozen=True, slots=True)
class PageRequest:
    """Bounded offset pagination request."""

    limit: int
    offset: int


@dataclass(frozen=True, slots=True)
class ContentRetrievalSummary:
    """Compact content metadata without extracted text."""

    id: int
    paper_id: int
    content_type: str
    extraction_status: str
    parser_version: str
    checksum: str | None
    source_filename: str | None
    source_media_type: str | None
    source_sha256: str | None
    access_basis: str | None
    page_count: int | None
    text_page_count: int | None
    extractor_name: str | None
    extractor_library_version: str | None
    extraction_error: str | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class RelevanceRetrievalSummary:
    """Compact current relevance summary for retrieval responses."""

    id: int
    paper_id: int
    paper_content_id: int
    analysis_scope: str
    rule_label: str
    rule_score: float
    normalized_score: float
    category_scores: dict[str, float]
    matched_concepts: tuple[str, ...]
    rule_version: str
    ontology_version: str
    model_version: str
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class AnalysisRetrievalSummary:
    """Compact analysis availability summary."""

    id: int
    paper_id: int
    paper_content_id: int
    analysis_scope: str
    status: str
    schema_version: str
    provider: str
    model: str
    prompt_version: str
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class PaperRetrievalSummary:
    """Paper metadata and related-resource summaries."""

    id: int
    doi: str | None
    normalized_doi: str | None
    title: str
    normalized_title: str
    journal: str | None
    publication_date: date | None
    source_url: str | None
    ingestion_source: str
    provider_record_id: str | None
    created_at: datetime
    updated_at: datetime
    contents: tuple[ContentRetrievalSummary, ...]
    relevance: RelevanceRetrievalSummary | None
    analyses: tuple[AnalysisRetrievalSummary, ...]
    abstract: str | None = None


@dataclass(frozen=True, slots=True)
class PaperSearchResult:
    """One page of paper retrieval results."""

    items: tuple[PaperRetrievalSummary, ...]
    total: int
    limit: int
    offset: int
    sort: PaperSort


@dataclass(frozen=True, slots=True)
class PaperChunkRetrievalSummary:
    """One explicit evidence chunk retrieval result."""

    id: int
    paper_id: int
    paper_content_id: int
    section: str
    heading: str | None
    sequence_number: int
    text: str
    start_char: int
    end_char: int
    paragraph_start_sequence: int
    paragraph_end_sequence: int
    token_count: int
    page_number: int | None
    end_page_number: int | None
    chunker_version: str
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class PaperChunkSearchResult:
    """One page of explicit paper chunks."""

    items: tuple[PaperChunkRetrievalSummary, ...]
    total: int
    limit: int
    offset: int


JsonObject = dict[str, Any]
