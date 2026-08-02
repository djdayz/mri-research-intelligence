from datetime import UTC, date, datetime

from mrinsight.nlp import compute_text_checksum
from mrinsight.papers import (
    AnalysisScope,
    ContentType,
    ExtractionStatus,
    SectionType,
    StoredPaperChunk,
    StoredPaperContent,
)
from mrinsight.papers.records import StoredPaper


def make_paper() -> StoredPaper:
    """Create a stored paper for analysis tests."""

    now = datetime.now(tz=UTC)
    return StoredPaper(
        id=1,
        doi="10.1234/analysis",
        normalized_doi="10.1234/analysis",
        title="BOLD MRI methods",
        normalized_title="bold mri methods",
        abstract="MRI methods reported 2.5 units.",
        journal="MRInsight Tests",
        publication_date=date(2026, 1, 1),
        source_url=None,
        ingestion_source="test",
        provider_record_id="record-1",
        created_at=now,
        updated_at=now,
    )


def make_content(
    *,
    content_type: ContentType = ContentType.ABSTRACT,
) -> StoredPaperContent:
    """Create successful content for analysis tests."""

    now = datetime.now(tz=UTC)
    text = "MRI methods reported 2.5 units."
    return StoredPaperContent(
        id=2,
        paper_id=1,
        content_type=content_type,
        extraction_status=ExtractionStatus.SUCCEEDED,
        extracted_text=text,
        parser_version="test",
        checksum=compute_text_checksum(text),
        created_at=now,
        updated_at=now,
    )


def make_chunk(
    *,
    chunk_id: int = 3,
    section: SectionType = SectionType.METHODS,
    sequence_number: int = 1,
    text: str = "MRI methods reported 2.5 units.",
) -> StoredPaperChunk:
    """Create a stored evidence chunk for analysis tests."""

    now = datetime.now(tz=UTC)
    return StoredPaperChunk(
        id=chunk_id,
        paper_id=1,
        paper_content_id=2,
        section_type=section,
        heading="Methods",
        sequence_number=sequence_number,
        text=text,
        start_char=0,
        end_char=len(text),
        paragraph_start_sequence=1,
        paragraph_end_sequence=1,
        token_count=len(text.split()),
        page_number=1,
        end_page_number=1,
        chunker_version="test",
        created_at=now,
        updated_at=now,
    )


def default_scope() -> AnalysisScope:
    """Return the default analysis scope for helper content."""

    return AnalysisScope.ABSTRACT_ONLY
