from datetime import UTC, datetime

from mrinsight.application.services import (
    ContentWriteOutcome,
    StoreAbstractContentService,
)
from mrinsight.papers import (
    ContentType,
    ExtractionStatus,
    NewPaperContent,
    StoredPaperContent,
)
from mrinsight.papers.repositories import (
    PaperContentNotFoundError,
)


class InMemoryPaperContentRepository:
    """In-memory repository for content-service tests."""

    def __init__(self) -> None:
        self._records: dict[
            tuple[int, ContentType],
            StoredPaperContent,
        ] = {}
        self._records_by_id: dict[
            int,
            StoredPaperContent,
        ] = {}
        self._next_id = 1

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
        now = datetime.now(UTC)

        stored = StoredPaperContent(
            id=self._next_id,
            paper_id=content.paper_id,
            content_type=content.content_type,
            extraction_status=(content.extraction_status),
            extracted_text=content.extracted_text,
            parser_version=content.parser_version,
            checksum=content.checksum,
            created_at=now,
            updated_at=now,
        )

        self._next_id += 1
        key = (
            stored.paper_id,
            stored.content_type,
        )
        self._records[key] = stored
        self._records_by_id[stored.id] = stored

        return stored

    def update_extraction(
        self,
        content_id: int,
        *,
        extraction_status: ExtractionStatus,
        extracted_text: str | None,
        parser_version: str,
        checksum: str | None,
    ) -> StoredPaperContent:
        existing = self._records_by_id.get(content_id)

        if existing is None:
            raise PaperContentNotFoundError(
                f"Paper content {content_id} does not exist."
            )

        updated = StoredPaperContent(
            id=existing.id,
            paper_id=existing.paper_id,
            content_type=existing.content_type,
            extraction_status=extraction_status,
            extracted_text=extracted_text,
            parser_version=parser_version,
            checksum=checksum,
            created_at=existing.created_at,
            updated_at=datetime.now(UTC),
        )

        key = (
            updated.paper_id,
            updated.content_type,
        )
        self._records[key] = updated
        self._records_by_id[updated.id] = updated

        return updated


def test_abstract_service_creates_cleaned_content() -> None:
    repository = InMemoryPaperContentRepository()
    service = StoreAbstractContentService(repository)

    result = service.execute(
        paper_id=1,
        abstract=("  MRI\tmethods.\r\n\r\nRMSE improved.  "),
    )

    assert result.outcome is ContentWriteOutcome.CREATED
    assert result.content is not None
    assert result.content.extracted_text == ("MRI methods.\n\nRMSE improved.")
    assert result.content.checksum is not None


def test_equivalent_abstract_is_not_rewritten() -> None:
    repository = InMemoryPaperContentRepository()
    service = StoreAbstractContentService(repository)

    first = service.execute(
        paper_id=1,
        abstract="MRI   methods.\r\n\r\nResults.",
    )
    second = service.execute(
        paper_id=1,
        abstract="MRI methods.\n\nResults.",
    )

    assert first.outcome is ContentWriteOutcome.CREATED
    assert second.outcome is (ContentWriteOutcome.UNCHANGED)
    assert first.content is not None
    assert second.content is not None
    assert second.content.id == first.content.id
    assert second.content.updated_at == (first.content.updated_at)


def test_changed_abstract_updates_existing_record() -> None:
    repository = InMemoryPaperContentRepository()
    service = StoreAbstractContentService(repository)

    first = service.execute(
        paper_id=1,
        abstract="Initial MRI abstract.",
    )
    second = service.execute(
        paper_id=1,
        abstract="Updated MRI abstract with new results.",
    )

    assert first.outcome is ContentWriteOutcome.CREATED
    assert second.outcome is ContentWriteOutcome.UPDATED
    assert first.content is not None
    assert second.content is not None
    assert second.content.id == first.content.id
    assert second.content.checksum != first.content.checksum
    assert second.content.extracted_text == ("Updated MRI abstract with new results.")


def test_missing_abstract_is_skipped() -> None:
    repository = InMemoryPaperContentRepository()
    service = StoreAbstractContentService(repository)

    result = service.execute(
        paper_id=1,
        abstract=None,
    )

    assert result.outcome is ContentWriteOutcome.SKIPPED
    assert result.content is None
