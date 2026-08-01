from dataclasses import dataclass
from enum import StrEnum

from mrinsight.application.services.build_paper_chunks import (
    BuildPaperChunksResult,
    BuildPaperChunksService,
)
from mrinsight.documents import (
    PdfTextExtractionError,
    PdfUploadCandidate,
    PdfUploadPolicy,
    ValidatedPdfUpload,
    validate_pdf_upload,
)
from mrinsight.documents.extractors import (
    PdfDocumentInspector,
    PdfTextExtractor,
)
from mrinsight.nlp import compute_text_checksum
from mrinsight.papers import (
    ContentType,
    ExtractionStatus,
    NewPaperContent,
    NewPaperContentPage,
    StoredPaperContent,
    StoredPaperContentPage,
)
from mrinsight.papers.repositories import (
    PaperContentPageRepository,
    PaperContentRepository,
    PaperRepository,
)


class PaperNotFoundError(RuntimeError):
    """Raised when a requested paper does not exist."""


class FullTextIngestionOutcome(StrEnum):
    """Outcome of one PDF full-text ingestion request."""

    CREATED = "created"
    UPDATED = "updated"
    UNCHANGED = "unchanged"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class IngestFullTextResult:
    """Result of validating and extracting one PDF."""

    content: StoredPaperContent
    pages: tuple[StoredPaperContentPage, ...]
    chunk_build: BuildPaperChunksResult
    outcome: FullTextIngestionOutcome


class IngestFullTextService:
    """Validate, extract and persist one paper's full text."""

    def __init__(
        self,
        *,
        paper_repository: PaperRepository,
        content_repository: PaperContentRepository,
        page_repository: PaperContentPageRepository,
        chunk_service: BuildPaperChunksService,
        inspector: PdfDocumentInspector,
        extractor: PdfTextExtractor,
        policy: PdfUploadPolicy,
    ) -> None:
        self._paper_repository = paper_repository
        self._content_repository = content_repository
        self._page_repository = page_repository
        self._chunk_service = chunk_service
        self._inspector = inspector
        self._extractor = extractor
        self._policy = policy

    def execute(
        self,
        paper_id: int,
        candidate: PdfUploadCandidate,
    ) -> IngestFullTextResult:
        """Validate, extract, persist and chunk one full-text PDF."""

        paper = self._paper_repository.get_by_id(paper_id)

        if paper is None:
            raise PaperNotFoundError(f"Paper {paper_id} does not exist.")

        validated = validate_pdf_upload(
            candidate,
            inspector=self._inspector,
            policy=self._policy,
        )

        existing = self._content_repository.get_by_paper_and_type(
            paper_id,
            ContentType.FULL_TEXT,
        )

        reusable = self._reuse_if_current(
            existing,
            validated,
        )

        if reusable is not None:
            return reusable

        try:
            extracted = self._extractor.extract(validated)
        except PdfTextExtractionError as error:
            return self._store_failure(
                paper_id=paper_id,
                existing=existing,
                validated=validated,
                error=error,
            )

        checksum = compute_text_checksum(extracted.text)

        content_values = NewPaperContent(
            paper_id=paper_id,
            content_type=ContentType.FULL_TEXT,
            extraction_status=ExtractionStatus.SUCCEEDED,
            extracted_text=extracted.text,
            parser_version=extracted.extractor_version,
            checksum=checksum,
            source_filename=validated.filename,
            source_media_type=validated.content_type,
            source_sha256=validated.sha256,
            access_basis=validated.access_basis.value,
            page_count=extracted.page_count,
            text_page_count=extracted.text_page_count,
            extractor_name=extracted.extractor_name,
            extractor_library_version=extracted.library_version,
            extraction_error=None,
        )

        if existing is None:
            stored_content = self._content_repository.add(content_values)
            outcome = FullTextIngestionOutcome.CREATED
        else:
            stored_content = self._content_repository.update_extraction(
                existing.id,
                extraction_status=content_values.extraction_status,
                extracted_text=content_values.extracted_text,
                parser_version=content_values.parser_version,
                checksum=content_values.checksum,
                source_filename=content_values.source_filename,
                source_media_type=content_values.source_media_type,
                source_sha256=content_values.source_sha256,
                access_basis=content_values.access_basis,
                page_count=content_values.page_count,
                text_page_count=content_values.text_page_count,
                extractor_name=content_values.extractor_name,
                extractor_library_version=(content_values.extractor_library_version),
                extraction_error=None,
            )
            outcome = FullTextIngestionOutcome.UPDATED

        page_values = tuple(
            NewPaperContentPage(
                paper_content_id=stored_content.id,
                page_number=page.page_number,
                text=page.text,
                start_char=page.start_char,
                end_char=page.end_char,
            )
            for page in extracted.pages
        )

        stored_pages = self._page_repository.replace_for_content(
            stored_content.id,
            page_values,
        )

        chunk_build = self._chunk_service.execute(
            stored_content,
            pages=stored_pages,
        )

        return IngestFullTextResult(
            content=stored_content,
            pages=stored_pages,
            chunk_build=chunk_build,
            outcome=outcome,
        )

    def _reuse_if_current(
        self,
        existing: StoredPaperContent | None,
        validated: ValidatedPdfUpload,
    ) -> IngestFullTextResult | None:
        """Reuse existing extraction when source and extractor match."""

        if existing is None:
            return None

        if not (
            existing.extraction_status is ExtractionStatus.SUCCEEDED
            and existing.source_sha256 == validated.sha256
            and existing.parser_version == self._extractor.version
            and existing.extractor_name == self._extractor.name
            and existing.extractor_library_version == self._extractor.library_version
            and existing.text_page_count is not None
        ):
            return None

        pages = self._page_repository.list_by_content(existing.id)

        if len(pages) != existing.text_page_count:
            return None

        chunk_build = self._chunk_service.execute(
            existing,
            pages=pages,
        )

        return IngestFullTextResult(
            content=existing,
            pages=pages,
            chunk_build=chunk_build,
            outcome=FullTextIngestionOutcome.UNCHANGED,
        )

    def _store_failure(
        self,
        *,
        paper_id: int,
        existing: StoredPaperContent | None,
        validated: ValidatedPdfUpload,
        error: PdfTextExtractionError,
    ) -> IngestFullTextResult:
        """Persist failed extraction provenance."""

        error_message = str(error).strip() or "PDF text extraction failed."

        values = NewPaperContent(
            paper_id=paper_id,
            content_type=ContentType.FULL_TEXT,
            extraction_status=ExtractionStatus.FAILED,
            extracted_text=None,
            parser_version=self._extractor.version,
            checksum=None,
            source_filename=validated.filename,
            source_media_type=validated.content_type,
            source_sha256=validated.sha256,
            access_basis=validated.access_basis.value,
            page_count=validated.page_count,
            text_page_count=0,
            extractor_name=self._extractor.name,
            extractor_library_version=self._extractor.library_version,
            extraction_error=error_message,
        )

        if existing is None:
            failed_content = self._content_repository.add(values)
        else:
            failed_content = self._content_repository.update_extraction(
                existing.id,
                extraction_status=ExtractionStatus.FAILED,
                extracted_text=None,
                parser_version=self._extractor.version,
                checksum=None,
                source_filename=validated.filename,
                source_media_type=validated.content_type,
                source_sha256=validated.sha256,
                access_basis=validated.access_basis.value,
                page_count=validated.page_count,
                text_page_count=0,
                extractor_name=self._extractor.name,
                extractor_library_version=(self._extractor.library_version),
                extraction_error=error_message,
            )

        self._page_repository.replace_for_content(
            failed_content.id,
            (),
        )

        chunk_build = self._chunk_service.execute(
            failed_content,
            pages=(),
        )

        return IngestFullTextResult(
            content=failed_content,
            pages=(),
            chunk_build=chunk_build,
            outcome=FullTextIngestionOutcome.FAILED,
        )
