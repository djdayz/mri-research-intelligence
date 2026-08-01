from collections.abc import Sequence
from datetime import UTC, date, datetime
from hashlib import sha256

from mrinsight.application.services import (
    BuildPaperChunksService,
    ChunkWriteOutcome,
    FullTextIngestionOutcome,
    IngestFullTextService,
)
from mrinsight.documents import (
    DocumentAccessBasis,
    ExtractedPdfDocument,
    ExtractedPdfPage,
    PdfInspection,
    PdfTextUnavailableError,
    PdfUploadCandidate,
    PdfUploadPolicy,
    ValidatedPdfUpload,
)
from mrinsight.papers import (
    ContentType,
    ExtractionStatus,
    NewPaper,
    NewPaperChunk,
    NewPaperContent,
    NewPaperContentPage,
    SectionType,
    StoredPaper,
    StoredPaperChunk,
    StoredPaperContent,
    StoredPaperContentPage,
)
from mrinsight.papers.repositories import (
    PaperContentNotFoundError,
)


class InMemoryPaperRepository:
    """Paper repository test double."""

    def __init__(self) -> None:
        now = datetime.now(UTC)
        self._paper = StoredPaper(
            id=1,
            doi="10.1234/mri.example",
            normalized_doi="10.1234/mri.example",
            title="MRI Example",
            normalized_title="mri example",
            abstract="An abstract.",
            journal="Journal of MRI Research",
            publication_date=date(2026, 3, 15),
            source_url="https://doi.org/10.1234/mri.example",
            ingestion_source="fake",
            provider_record_id="record-001",
            created_at=now,
            updated_at=now,
        )

    def get_by_id(
        self,
        paper_id: int,
    ) -> StoredPaper | None:
        if paper_id == self._paper.id:
            return self._paper

        return None

    def get_by_normalized_doi(
        self,
        normalized_doi: str,
    ) -> StoredPaper | None:
        if normalized_doi == self._paper.normalized_doi:
            return self._paper

        return None

    def add(
        self,
        paper: NewPaper,
    ) -> StoredPaper:
        del paper

        return self._paper


class InMemoryPaperContentRepository:
    """Content repository test double."""

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
            source_filename=content.source_filename,
            source_media_type=content.source_media_type,
            source_sha256=content.source_sha256,
            access_basis=content.access_basis,
            page_count=content.page_count,
            text_page_count=content.text_page_count,
            extractor_name=content.extractor_name,
            extractor_library_version=(content.extractor_library_version),
            extraction_error=content.extraction_error,
            created_at=now,
            updated_at=now,
        )

        self._next_id += 1
        self._store(stored)

        return stored

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
            source_filename=source_filename,
            source_media_type=source_media_type,
            source_sha256=source_sha256,
            access_basis=access_basis,
            page_count=page_count,
            text_page_count=text_page_count,
            extractor_name=extractor_name,
            extractor_library_version=extractor_library_version,
            extraction_error=extraction_error,
            created_at=existing.created_at,
            updated_at=datetime.now(UTC),
        )
        self._store(updated)

        return updated

    def _store(
        self,
        content: StoredPaperContent,
    ) -> None:
        self._records[(content.paper_id, content.content_type)] = content
        self._records_by_id[content.id] = content


class InMemoryPaperContentPageRepository:
    """Content-page repository test double."""

    def __init__(self) -> None:
        self._records: dict[int, tuple[StoredPaperContentPage, ...]] = {}
        self._next_id = 1

    def list_by_content(
        self,
        paper_content_id: int,
    ) -> tuple[StoredPaperContentPage, ...]:
        return self._records.get(paper_content_id, ())

    def replace_for_content(
        self,
        paper_content_id: int,
        pages: Sequence[NewPaperContentPage],
    ) -> tuple[StoredPaperContentPage, ...]:
        now = datetime.now(UTC)
        stored_pages: list[StoredPaperContentPage] = []

        for page in pages:
            stored = StoredPaperContentPage(
                id=self._next_id,
                paper_content_id=paper_content_id,
                page_number=page.page_number,
                text=page.text,
                start_char=page.start_char,
                end_char=page.end_char,
                created_at=now,
            )
            self._next_id += 1
            stored_pages.append(stored)

        self._records[paper_content_id] = tuple(stored_pages)

        return tuple(stored_pages)


class InMemoryPaperChunkRepository:
    """Chunk repository test double."""

    def __init__(self) -> None:
        self._chunks: dict[int, tuple[StoredPaperChunk, ...]] = {}
        self._next_id = 1

    def list_by_content(
        self,
        paper_content_id: int,
    ) -> tuple[StoredPaperChunk, ...]:
        return self._chunks.get(paper_content_id, ())

    def add_many(
        self,
        chunks: Sequence[NewPaperChunk],
    ) -> tuple[StoredPaperChunk, ...]:
        now = datetime.now(UTC)
        stored_chunks: list[StoredPaperChunk] = []

        for chunk in chunks:
            stored = StoredPaperChunk(
                id=self._next_id,
                paper_id=chunk.paper_id,
                paper_content_id=chunk.paper_content_id,
                section_type=chunk.section_type,
                heading=chunk.heading,
                sequence_number=chunk.sequence_number,
                text=chunk.text,
                start_char=chunk.start_char,
                end_char=chunk.end_char,
                paragraph_start_sequence=chunk.paragraph_start_sequence,
                paragraph_end_sequence=chunk.paragraph_end_sequence,
                token_count=chunk.token_count,
                page_number=chunk.page_number,
                chunker_version=chunk.chunker_version,
                created_at=now,
                updated_at=now,
                end_page_number=chunk.end_page_number,
            )
            self._next_id += 1
            stored_chunks.append(stored)

        if stored_chunks:
            self._chunks[stored_chunks[0].paper_content_id] = tuple(stored_chunks)

        return tuple(stored_chunks)

    def delete_by_content(
        self,
        paper_content_id: int,
    ) -> int:
        existing = self._chunks.pop(paper_content_id, ())

        return len(existing)


class FakePdfInspector:
    """PDF inspector test double."""

    @property
    def name(self) -> str:
        return "fake-pdf"

    def inspect(
        self,
        data: bytes,
    ) -> PdfInspection:
        del data

        return PdfInspection(
            page_count=2,
            pdf_header="%PDF-1.7",
        )


class FakePdfExtractor:
    """PDF extractor test double."""

    def __init__(self) -> None:
        self._documents: dict[str, ExtractedPdfDocument] = {}
        self.failures_remaining = 0
        self.call_count = 0

    @property
    def name(self) -> str:
        return "fake-pdf"

    @property
    def version(self) -> str:
        return "fake-layout-v1"

    @property
    def library_version(self) -> str:
        return "fake-pdf-lib-1.0"

    def register_document(
        self,
        data: bytes,
        page_texts: tuple[str, ...],
    ) -> None:
        self._documents[sha256(data).hexdigest()] = make_extracted_document(
            data,
            page_texts,
            extractor_name=self.name,
            extractor_version=self.version,
            library_version=self.library_version,
        )

    def extract(
        self,
        document: ValidatedPdfUpload,
    ) -> ExtractedPdfDocument:
        self.call_count += 1

        if self.failures_remaining:
            self.failures_remaining -= 1
            raise PdfTextUnavailableError("PDF contains no extractable text.")

        return self._documents[document.sha256]


content_repository: InMemoryPaperContentRepository
page_repository: InMemoryPaperContentPageRepository
chunk_repository: InMemoryPaperChunkRepository


def make_extracted_document(
    data: bytes,
    page_texts: tuple[str, ...],
    *,
    extractor_name: str,
    extractor_version: str,
    library_version: str,
) -> ExtractedPdfDocument:
    """Build page-aware extracted PDF text."""

    pages: list[ExtractedPdfPage] = []
    text_parts: list[str] = []
    current_offset = 0

    for index, text in enumerate(page_texts, start=1):
        if text_parts:
            text_parts.append("\n\n")
            current_offset += 2

        start_char = current_offset
        text_parts.append(text)
        current_offset += len(text)

        pages.append(
            ExtractedPdfPage(
                page_number=index,
                text=text,
                start_char=start_char,
                end_char=current_offset,
            )
        )

    return ExtractedPdfDocument(
        text="".join(text_parts),
        pages=tuple(pages),
        page_count=len(page_texts),
        text_page_count=len(page_texts),
        source_sha256=sha256(data).hexdigest(),
        extractor_name=extractor_name,
        extractor_version=extractor_version,
        library_version=library_version,
    )


def make_candidate(
    data: bytes,
) -> PdfUploadCandidate:
    """Create a PDF upload candidate."""

    return PdfUploadCandidate(
        filename="paper.pdf",
        content_type="application/pdf",
        data=data,
        access_basis=DocumentAccessBasis.USER_UPLOAD,
    )


def make_service(
    extractor: FakePdfExtractor,
) -> IngestFullTextService:
    """Create the full-text ingestion service with in-memory dependencies."""

    return IngestFullTextService(
        paper_repository=InMemoryPaperRepository(),
        content_repository=content_repository,
        page_repository=page_repository,
        chunk_service=BuildPaperChunksService(chunk_repository),
        inspector=FakePdfInspector(),
        extractor=extractor,
        policy=PdfUploadPolicy(),
    )


PDF_BYTES = b"%PDF-1.7\nfirst"
UPDATED_PDF_BYTES = b"%PDF-1.7\nsecond"

INITIAL_PAGE_TEXTS = (
    "Methods\nInitial MRI results.",
    "Second MRI paragraph.",
)
UPDATED_PAGE_TEXTS = (
    "Methods\nUpdated MRI results.",
    "External validation paragraph.",
)


def setup_function() -> None:
    """Reset in-memory repositories for each test."""

    global content_repository, page_repository, chunk_repository

    content_repository = InMemoryPaperContentRepository()
    page_repository = InMemoryPaperContentPageRepository()
    chunk_repository = InMemoryPaperChunkRepository()


def test_full_text_service_creates_content_pages_and_chunks() -> None:
    extractor = FakePdfExtractor()
    extractor.register_document(PDF_BYTES, INITIAL_PAGE_TEXTS)
    service = make_service(extractor)

    result = service.execute(
        1,
        make_candidate(PDF_BYTES),
    )

    assert result.outcome is FullTextIngestionOutcome.CREATED
    assert result.content.extraction_status is ExtractionStatus.SUCCEEDED
    assert result.content.source_sha256 == sha256(PDF_BYTES).hexdigest()

    assert len(result.pages) == 2
    assert result.content.extracted_text is not None

    for page in result.pages:
        assert (
            result.content.extracted_text[page.start_char : page.end_char] == page.text
        )

    assert len(result.chunk_build.chunks) == 1
    assert result.chunk_build.chunks[0].section_type is SectionType.METHODS
    assert result.chunk_build.chunks[0].page_number == 1
    assert result.chunk_build.chunks[0].end_page_number == 2


def test_repeated_identical_upload_is_unchanged() -> None:
    extractor = FakePdfExtractor()
    extractor.register_document(PDF_BYTES, INITIAL_PAGE_TEXTS)
    service = make_service(extractor)

    first = service.execute(
        1,
        make_candidate(PDF_BYTES),
    )
    second = service.execute(
        1,
        make_candidate(PDF_BYTES),
    )

    assert second.outcome is FullTextIngestionOutcome.UNCHANGED
    assert extractor.call_count == 1
    assert second.content.id == first.content.id
    assert [page.id for page in second.pages] == [page.id for page in first.pages]
    assert [chunk.id for chunk in second.chunk_build.chunks] == [
        chunk.id for chunk in first.chunk_build.chunks
    ]


def test_changed_pdf_updates_full_text() -> None:
    extractor = FakePdfExtractor()
    extractor.register_document(PDF_BYTES, INITIAL_PAGE_TEXTS)
    extractor.register_document(UPDATED_PDF_BYTES, UPDATED_PAGE_TEXTS)
    service = make_service(extractor)

    first = service.execute(
        1,
        make_candidate(PDF_BYTES),
    )
    second = service.execute(
        1,
        make_candidate(UPDATED_PDF_BYTES),
    )

    assert first.outcome is FullTextIngestionOutcome.CREATED
    assert second.outcome is FullTextIngestionOutcome.UPDATED
    assert second.content.id == first.content.id
    assert second.content.source_sha256 != first.content.source_sha256
    assert second.pages[0].text == UPDATED_PAGE_TEXTS[0]
    assert "Updated MRI results." in second.chunk_build.chunks[0].text


def test_textless_pdf_persists_failed_content() -> None:
    extractor = FakePdfExtractor()
    extractor.register_document(PDF_BYTES, INITIAL_PAGE_TEXTS)
    extractor.failures_remaining = 1
    service = make_service(extractor)

    result = service.execute(
        1,
        make_candidate(PDF_BYTES),
    )

    assert result.outcome is FullTextIngestionOutcome.FAILED
    assert result.content.extraction_status is ExtractionStatus.FAILED
    assert result.content.extracted_text is None
    assert result.content.checksum is None
    assert result.content.text_page_count == 0
    assert result.content.extraction_error == ("PDF contains no extractable text.")
    assert result.pages == ()
    assert result.chunk_build.chunks == ()
    assert result.chunk_build.outcome is ChunkWriteOutcome.SKIPPED


def test_successful_reupload_recovers_failed_full_text() -> None:
    extractor = FakePdfExtractor()
    extractor.register_document(PDF_BYTES, INITIAL_PAGE_TEXTS)
    extractor.failures_remaining = 1
    service = make_service(extractor)

    first = service.execute(
        1,
        make_candidate(PDF_BYTES),
    )

    assert first.outcome is FullTextIngestionOutcome.FAILED

    second = service.execute(
        1,
        make_candidate(PDF_BYTES),
    )

    assert second.outcome is FullTextIngestionOutcome.UPDATED
    assert second.content.id == first.content.id
    assert second.content.extraction_status is ExtractionStatus.SUCCEEDED
    assert second.content.extraction_error is None
    assert second.pages
    assert second.chunk_build.chunks
