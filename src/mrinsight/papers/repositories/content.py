from typing import Protocol

from mrinsight.papers.content import (
    ContentType,
    ExtractionStatus,
)
from mrinsight.papers.content_records import (
    NewPaperContent,
    StoredPaperContent,
)


class PaperContentNotFoundError(RuntimeError):
    """Raised when requested paper content does not exist."""


class PaperContentRepository(Protocol):
    """Persistence contract for scientific paper content."""

    def get_by_paper_and_type(
        self,
        paper_id: int,
        content_type: ContentType,
    ) -> StoredPaperContent | None:
        """Return one current content record, if present."""

        ...

    def add(
        self,
        content: NewPaperContent,
    ) -> StoredPaperContent:
        """Persist new content without committing."""

        ...

    def update_extraction(
        self,
        content_id: int,
        *,
        extraction_status: ExtractionStatus,
        extracted_text: str | None,
        parser_version: str,
        checksum: str | None,
        source_filename: str | None = None,
        source_media_type: str | None = None,
        source_sha256: str | None = None,
        access_basis: str | None = None,
        page_count: int | None = None,
        text_page_count: int | None = None,
        extractor_name: str | None = None,
        extractor_library_version: str | None = None,
        extraction_error: str | None = None,
    ) -> StoredPaperContent:
        """Replace extraction state without committing."""

        ...
