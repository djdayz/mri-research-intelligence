from pydantic import BaseModel

from mrinsight.application.services import (
    FullTextIngestionOutcome,
    IngestFullTextResult,
)
from mrinsight.papers import (
    AnalysisScope,
    ExtractionStatus,
)


class FullTextUploadResponse(BaseModel):
    """Result of uploading one paper PDF."""

    paper_id: int
    content_id: int
    outcome: FullTextIngestionOutcome
    extraction_status: ExtractionStatus
    analysis_scope: AnalysisScope | None
    source_sha256: str
    page_count: int
    text_page_count: int
    chunk_count: int
    error: str | None

    @classmethod
    def from_result(
        cls,
        *,
        paper_id: int,
        result: IngestFullTextResult,
        analysis_scope: AnalysisScope | None,
    ) -> "FullTextUploadResponse":
        """Build the API response from an ingestion result."""

        content = result.content

        if (
            content.source_sha256 is None
            or content.page_count is None
            or content.text_page_count is None
        ):
            raise ValueError("Full-text result is missing provenance.")

        return cls(
            paper_id=paper_id,
            content_id=content.id,
            outcome=result.outcome,
            extraction_status=content.extraction_status,
            analysis_scope=analysis_scope,
            source_sha256=content.source_sha256,
            page_count=content.page_count,
            text_page_count=content.text_page_count,
            chunk_count=len(result.chunk_build.chunks),
            error=content.extraction_error,
        )
