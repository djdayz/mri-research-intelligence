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
    ) -> StoredPaperContent:
        """Replace the extraction state without committing."""

        ...
