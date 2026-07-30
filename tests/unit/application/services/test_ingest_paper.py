from datetime import UTC, date, datetime

import pytest
from pydantic import HttpUrl

from mrinsight.application.services import (
    BibliographicIdentityMismatchError,
    ContentWriteOutcome,
    IngestPaperService,
    StoreAbstractContentService,
)
from mrinsight.papers import (
    ContentType,
    ExtractionStatus,
    NewPaper,
    NewPaperContent,
    ResolvedPaperMetadata,
    StoredPaper,
    StoredPaperContent,
)
from mrinsight.papers.repositories import PaperContentNotFoundError


class InMemoryPaperRepository:
    """Small repository test double for service tests."""

    def __init__(self) -> None:
        self._records: dict[str, StoredPaper] = {}
        self._next_id = 1

    def get_by_normalized_doi(
        self,
        normalized_doi: str,
    ) -> StoredPaper | None:
        return self._records.get(normalized_doi)

    def add(
        self,
        paper: NewPaper,
    ) -> StoredPaper:
        now = datetime.now(UTC)

        stored = StoredPaper(
            id=self._next_id,
            doi=paper.doi,
            normalized_doi=paper.normalized_doi,
            title=paper.title,
            normalized_title=paper.normalized_title,
            abstract=paper.abstract,
            journal=paper.journal,
            publication_date=paper.publication_date,
            source_url=paper.source_url,
            ingestion_source=paper.ingestion_source,
            provider_record_id=paper.provider_record_id,
            created_at=now,
            updated_at=now,
        )

        self._next_id += 1

        if stored.normalized_doi is not None:
            self._records[stored.normalized_doi] = stored

        return stored


class CountingBibliographicProvider:
    """Return one record and count resolution calls."""

    def __init__(
        self,
        record: ResolvedPaperMetadata,
    ) -> None:
        self._record = record
        self.resolve_calls = 0

    @property
    def name(self) -> str:
        return "fake"

    def resolve_by_doi(
        self,
        doi: str,
    ) -> ResolvedPaperMetadata:
        self.resolve_calls += 1
        return self._record


class InMemoryPaperContentRepository:
    """Small content repository test double."""

    def __init__(self) -> None:
        self._records: dict[tuple[int, ContentType], StoredPaperContent] = {}
        self._records_by_id: dict[int, StoredPaperContent] = {}
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
            extraction_status=content.extraction_status,
            extracted_text=content.extracted_text,
            parser_version=content.parser_version,
            checksum=content.checksum,
            created_at=now,
            updated_at=now,
        )

        self._next_id += 1
        self._records[(stored.paper_id, stored.content_type)] = stored
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

        self._records[(updated.paper_id, updated.content_type)] = updated
        self._records_by_id[updated.id] = updated

        return updated


def make_ingestion_service(
    provider: CountingBibliographicProvider,
    paper_repository: InMemoryPaperRepository,
) -> IngestPaperService:
    content_repository = InMemoryPaperContentRepository()

    return IngestPaperService(
        provider=provider,
        repository=paper_repository,
        abstract_content_service=StoreAbstractContentService(content_repository),
    )


def make_metadata(
    doi: str = "10.1234/mri.example",
) -> ResolvedPaperMetadata:
    """Create valid resolved metadata."""

    return ResolvedPaperMetadata(
        doi=doi,
        title="Deep Learning for MRI Reconstruction",
        abstract="An MRI reconstruction study.",
        journal="Journal of MRI Research",
        publication_date=date(2026, 3, 15),
        source_url=HttpUrl("https://example.org/papers/mri-example"),
        authors=("Alice Smith", "Bob Jones"),
        provider_name="fake",
        provider_record_id="record-001",
    )


def test_ingestion_creates_new_paper() -> None:
    provider = CountingBibliographicProvider(make_metadata())
    repository = InMemoryPaperRepository()
    service = make_ingestion_service(
        provider,
        repository,
    )

    result = service.execute("https://doi.org/10.1234/MRI.EXAMPLE")

    assert result.created is True
    assert result.paper.normalized_doi == ("10.1234/mri.example")
    assert result.paper.normalized_title == ("deep learning for mri reconstruction")
    assert result.paper.ingestion_source == "fake"
    assert result.abstract_content.outcome is (ContentWriteOutcome.CREATED)
    assert result.abstract_content.content is not None
    assert result.abstract_content.content.content_type is (ContentType.ABSTRACT)
    assert provider.resolve_calls == 1


def test_repeated_ingestion_reuses_existing_paper() -> None:
    provider = CountingBibliographicProvider(make_metadata())
    repository = InMemoryPaperRepository()
    service = make_ingestion_service(
        provider,
        repository,
    )

    first = service.execute("10.1234/MRI.EXAMPLE")
    second = service.execute("https://doi.org/10.1234/mri.example")

    assert first.created is True
    assert second.created is False
    assert second.paper.id == first.paper.id
    assert second.abstract_content.outcome is (ContentWriteOutcome.UNCHANGED)
    assert provider.resolve_calls == 1


def test_ingestion_rejects_provider_doi_mismatch() -> None:
    provider = CountingBibliographicProvider(make_metadata("10.9999/different.paper"))
    repository = InMemoryPaperRepository()
    service = make_ingestion_service(
        provider,
        repository,
    )

    with pytest.raises(
        BibliographicIdentityMismatchError,
        match="different.paper",
    ):
        service.execute("10.1234/requested.paper")
