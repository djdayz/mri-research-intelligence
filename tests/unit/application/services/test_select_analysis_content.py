from datetime import UTC, datetime

import pytest

from mrinsight.application.services import (
    NoAnalyzableContentError,
    SelectAnalysisContentService,
)
from mrinsight.papers import (
    AnalysisScope,
    ContentType,
    ExtractionStatus,
    NewPaperContent,
    StoredPaperContent,
)


class InMemoryPaperContentRepository:
    """Content repository test double for selector tests."""

    def __init__(
        self,
        records: tuple[StoredPaperContent, ...],
    ) -> None:
        self._records = {
            (record.paper_id, record.content_type): record for record in records
        }

    def get_by_paper_and_type(
        self,
        paper_id: int,
        content_type: ContentType,
    ) -> StoredPaperContent | None:
        return self._records.get((paper_id, content_type))

    def add(
        self,
        content: NewPaperContent,
    ) -> StoredPaperContent:
        del content

        raise NotImplementedError

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
        del (
            content_id,
            extraction_status,
            extracted_text,
            parser_version,
            checksum,
            source_filename,
            source_media_type,
            source_sha256,
            access_basis,
            page_count,
            text_page_count,
            extractor_name,
            extractor_library_version,
            extraction_error,
        )

        raise NotImplementedError


def make_content(
    content_type: ContentType,
    *,
    status: ExtractionStatus = ExtractionStatus.SUCCEEDED,
    content_id: int = 1,
    text: str | None = "MRI evidence text.",
    checksum: str | None = "a" * 64,
    error: str | None = None,
) -> StoredPaperContent:
    """Create stored content for selector tests."""

    now = datetime.now(UTC)

    return StoredPaperContent(
        id=content_id,
        paper_id=1,
        content_type=content_type,
        extraction_status=status,
        extracted_text=text,
        parser_version="test-parser-v1",
        checksum=checksum,
        extraction_error=error,
        created_at=now,
        updated_at=now,
    )


def test_selector_prefers_successful_full_text() -> None:
    service = SelectAnalysisContentService(
        InMemoryPaperContentRepository(
            (
                make_content(
                    ContentType.ABSTRACT,
                    content_id=1,
                ),
                make_content(
                    ContentType.FULL_TEXT,
                    content_id=2,
                ),
            )
        )
    )

    result = service.execute(1)

    assert result.scope is AnalysisScope.FULL_TEXT


def test_selector_falls_back_to_abstract() -> None:
    service = SelectAnalysisContentService(
        InMemoryPaperContentRepository(
            (
                make_content(
                    ContentType.ABSTRACT,
                    content_id=1,
                ),
                make_content(
                    ContentType.FULL_TEXT,
                    status=ExtractionStatus.FAILED,
                    content_id=2,
                    text=None,
                    checksum=None,
                    error="Simulated extraction failure.",
                ),
            )
        )
    )

    result = service.execute(1)

    assert result.scope is AnalysisScope.ABSTRACT_ONLY


def test_selector_rejects_paper_without_successful_content() -> None:
    service = SelectAnalysisContentService(
        InMemoryPaperContentRepository(
            (
                make_content(
                    ContentType.FULL_TEXT,
                    status=ExtractionStatus.FAILED,
                    text=None,
                    checksum=None,
                    error="Simulated extraction failure.",
                ),
            )
        )
    )

    with pytest.raises(NoAnalyzableContentError):
        service.execute(1)
