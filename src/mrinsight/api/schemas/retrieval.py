from dataclasses import asdict
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from mrinsight.retrieval import (
    AnalysisRetrievalSummary,
    ContentRetrievalSummary,
    PaperChunkRetrievalSummary,
    PaperChunkSearchResult,
    PaperRetrievalSummary,
    PaperSearchResult,
    RelevanceRetrievalSummary,
)


class ContentSummaryResponse(BaseModel):
    """Public content metadata without extracted text."""

    model_config = ConfigDict(extra="forbid")

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

    @classmethod
    def from_summary(
        cls,
        summary: ContentRetrievalSummary,
    ) -> "ContentSummaryResponse":
        """Create response from retrieval summary."""

        return cls(**asdict(summary))


class RelevanceSummaryResponse(BaseModel):
    """Public compact relevance summary."""

    model_config = ConfigDict(extra="forbid")

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

    @classmethod
    def from_summary(
        cls,
        summary: RelevanceRetrievalSummary,
    ) -> "RelevanceSummaryResponse":
        """Create response from retrieval summary."""

        return cls(**asdict(summary))


class AnalysisSummaryResponse(BaseModel):
    """Public compact analysis availability summary."""

    model_config = ConfigDict(extra="forbid")

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

    @classmethod
    def from_summary(
        cls,
        summary: AnalysisRetrievalSummary,
    ) -> "AnalysisSummaryResponse":
        """Create response from retrieval summary."""

        return cls(**asdict(summary))


class PaperSummaryResponse(BaseModel):
    """Public paper summary for list responses."""

    model_config = ConfigDict(extra="forbid")

    id: int
    doi: str | None
    normalized_doi: str | None
    title: str
    normalized_title: str
    journal: str | None
    publication_date: date | None
    source_url: HttpUrl | None
    ingestion_source: str
    provider_record_id: str | None
    available_content_scopes: tuple[str, ...]
    extraction_states: tuple[ContentSummaryResponse, ...]
    relevance_summary: RelevanceSummaryResponse | None
    analysis_availability: tuple[AnalysisSummaryResponse, ...]
    related: dict[str, str]
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_summary(
        cls,
        summary: PaperRetrievalSummary,
    ) -> "PaperSummaryResponse":
        """Create response from retrieval summary."""

        return cls(
            id=summary.id,
            doi=summary.doi,
            normalized_doi=summary.normalized_doi,
            title=summary.title,
            normalized_title=summary.normalized_title,
            journal=summary.journal,
            publication_date=summary.publication_date,
            source_url=(
                HttpUrl(summary.source_url) if summary.source_url is not None else None
            ),
            ingestion_source=summary.ingestion_source,
            provider_record_id=summary.provider_record_id,
            available_content_scopes=tuple(
                content.content_type
                for content in summary.contents
                if content.extraction_status == "succeeded"
            ),
            extraction_states=tuple(
                ContentSummaryResponse.from_summary(content)
                for content in summary.contents
            ),
            relevance_summary=(
                RelevanceSummaryResponse.from_summary(summary.relevance)
                if summary.relevance is not None
                else None
            ),
            analysis_availability=tuple(
                AnalysisSummaryResponse.from_summary(analysis)
                for analysis in summary.analyses
            ),
            related={
                "self": f"/papers/{summary.id}",
                "contents": f"/papers/{summary.id}/contents",
                "chunks": f"/papers/{summary.id}/chunks",
                "relevance": f"/papers/{summary.id}/relevance",
                "analyses": f"/papers/{summary.id}/analysis",
            },
            created_at=summary.created_at,
            updated_at=summary.updated_at,
        )


class PaperDetailResponse(PaperSummaryResponse):
    """Public paper detail with bibliographic abstract."""

    abstract: str | None

    @classmethod
    def from_summary(
        cls,
        summary: PaperRetrievalSummary,
    ) -> "PaperDetailResponse":
        """Create detail response from retrieval summary."""

        base = PaperSummaryResponse.from_summary(summary).model_dump()

        return cls(
            **base,
            abstract=summary.abstract,
        )


class PaperSearchResponse(BaseModel):
    """Public bounded offset-paginated paper search response."""

    model_config = ConfigDict(extra="forbid")

    items: tuple[PaperSummaryResponse, ...]
    total: int = Field(ge=0)
    limit: int = Field(ge=1)
    offset: int = Field(ge=0)
    sort: str
    next_offset: int | None

    @classmethod
    def from_result(
        cls,
        result: PaperSearchResult,
    ) -> "PaperSearchResponse":
        """Create API response from search result."""

        candidate_next_offset = result.offset + result.limit
        next_offset: int | None = (
            candidate_next_offset if candidate_next_offset < result.total else None
        )

        return cls(
            items=tuple(
                PaperSummaryResponse.from_summary(item) for item in result.items
            ),
            total=result.total,
            limit=result.limit,
            offset=result.offset,
            sort=result.sort.value,
            next_offset=next_offset,
        )


class PaperChunkResponse(BaseModel):
    """Public explicit paper chunk response."""

    model_config = ConfigDict(extra="forbid")

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

    @classmethod
    def from_summary(
        cls,
        summary: PaperChunkRetrievalSummary,
    ) -> "PaperChunkResponse":
        """Create response from chunk summary."""

        return cls(**asdict(summary))


class PaperChunkSearchResponse(BaseModel):
    """Public bounded offset-paginated chunk response."""

    model_config = ConfigDict(extra="forbid")

    items: tuple[PaperChunkResponse, ...]
    total: int = Field(ge=0)
    limit: int = Field(ge=1)
    offset: int = Field(ge=0)
    next_offset: int | None

    @classmethod
    def from_result(
        cls,
        result: PaperChunkSearchResult,
    ) -> "PaperChunkSearchResponse":
        """Create API response from chunk search result."""

        candidate_next_offset = result.offset + result.limit
        next_offset: int | None = (
            candidate_next_offset if candidate_next_offset < result.total else None
        )

        return cls(
            items=tuple(PaperChunkResponse.from_summary(item) for item in result.items),
            total=result.total,
            limit=result.limit,
            offset=result.offset,
            next_offset=next_offset,
        )
