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
