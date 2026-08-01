from sqlalchemy import select
from sqlalchemy.orm import Session

from mrinsight.db.models import PaperContent
from mrinsight.papers.content import (
    ContentType,
    ExtractionStatus,
)
from mrinsight.papers.content_records import (
    NewPaperContent,
    StoredPaperContent,
)
from mrinsight.papers.repositories import (
    PaperContentNotFoundError,
)


class SqlAlchemyPaperContentRepository:
    """Persist scientific content using SQLAlchemy."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_paper_and_type(
        self,
        paper_id: int,
        content_type: ContentType,
    ) -> StoredPaperContent | None:
        """Return the current content record for one scope."""

        statement = select(PaperContent).where(
            PaperContent.paper_id == paper_id,
            PaperContent.content_type == content_type.value,
        )

        model = self._session.execute(statement).scalar_one_or_none()

        if model is None:
            return None

        return self._to_stored_content(model)

    def add(
        self,
        content: NewPaperContent,
    ) -> StoredPaperContent:
        """Insert content and flush without committing."""

        model = PaperContent(
            paper_id=content.paper_id,
            content_type=content.content_type.value,
            extraction_status=(content.extraction_status.value),
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
        )

        self._session.add(model)
        self._session.flush()
        self._session.refresh(model)

        return self._to_stored_content(model)

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
        """Update extraction fields and flush without committing."""

        model = self._session.get(
            PaperContent,
            content_id,
        )

        if model is None:
            raise PaperContentNotFoundError(
                f"Paper content {content_id} does not exist."
            )

        model.extraction_status = extraction_status.value
        model.extracted_text = extracted_text
        model.parser_version = parser_version
        model.checksum = checksum
        model.source_filename = source_filename
        model.source_media_type = source_media_type
        model.source_sha256 = source_sha256
        model.access_basis = access_basis
        model.page_count = page_count
        model.text_page_count = text_page_count
        model.extractor_name = extractor_name
        model.extractor_library_version = extractor_library_version
        model.extraction_error = extraction_error

        self._session.flush()
        self._session.refresh(model)

        return self._to_stored_content(model)

    @staticmethod
    def _to_stored_content(
        model: PaperContent,
    ) -> StoredPaperContent:
        """Translate an ORM model into an application value."""

        return StoredPaperContent(
            id=model.id,
            paper_id=model.paper_id,
            content_type=ContentType(model.content_type),
            extraction_status=ExtractionStatus(model.extraction_status),
            extracted_text=model.extracted_text,
            parser_version=model.parser_version,
            checksum=model.checksum,
            source_filename=model.source_filename,
            source_media_type=model.source_media_type,
            source_sha256=model.source_sha256,
            access_basis=model.access_basis,
            page_count=model.page_count,
            text_page_count=model.text_page_count,
            extractor_name=model.extractor_name,
            extractor_library_version=(model.extractor_library_version),
            extraction_error=model.extraction_error,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
