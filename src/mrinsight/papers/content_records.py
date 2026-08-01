from dataclasses import dataclass
from datetime import datetime

from mrinsight.papers.content import (
    ContentType,
    ExtractionStatus,
)


@dataclass(frozen=True, slots=True)
class NewPaperContent:
    """Scientific content ready to be persisted."""

    paper_id: int
    content_type: ContentType
    extraction_status: ExtractionStatus
    extracted_text: str | None
    parser_version: str
    checksum: str | None

    source_filename: str | None = None
    source_media_type: str | None = None
    source_sha256: str | None = None
    access_basis: str | None = None
    page_count: int | None = None
    text_page_count: int | None = None
    extractor_name: str | None = None
    extractor_library_version: str | None = None
    extraction_error: str | None = None


@dataclass(frozen=True, slots=True)
class StoredPaperContent:
    """Scientific content returned from persistence."""

    id: int
    paper_id: int
    content_type: ContentType
    extraction_status: ExtractionStatus
    extracted_text: str | None
    parser_version: str
    checksum: str | None
    created_at: datetime
    updated_at: datetime

    source_filename: str | None = None
    source_media_type: str | None = None
    source_sha256: str | None = None
    access_basis: str | None = None
    page_count: int | None = None
    text_page_count: int | None = None
    extractor_name: str | None = None
    extractor_library_version: str | None = None
    extraction_error: str | None = None
