from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from mrinsight.db.base import Base


class PaperContent(Base):
    """Extracted scientific text associated with one paper."""

    __tablename__ = "paper_contents"

    __table_args__ = (
        UniqueConstraint(
            "paper_id",
            "content_type",
            name=("uq_paper_contents_paper_id_content_type"),
        ),
        CheckConstraint(
            "content_type IN ('abstract', 'full_text')",
            name=("ck_paper_contents_supported_content_type"),
        ),
        CheckConstraint(
            "extraction_status IN ('succeeded', 'failed')",
            name=("ck_paper_contents_supported_extraction_status"),
        ),
        CheckConstraint(
            "("
            "extraction_status = 'succeeded' "
            "AND extracted_text IS NOT NULL "
            "AND checksum IS NOT NULL "
            "AND extraction_error IS NULL"
            ") OR ("
            "extraction_status = 'failed' "
            "AND extracted_text IS NULL "
            "AND checksum IS NULL "
            "AND extraction_error IS NOT NULL"
            ")",
            name=("ck_paper_contents_valid_extraction_state"),
        ),
        CheckConstraint(
            "access_basis IS NULL OR access_basis IN ('user_upload', 'open_access')",
            name=("ck_paper_contents_supported_access_basis"),
        ),
        CheckConstraint(
            "source_sha256 IS NULL OR length(source_sha256) = 64",
            name=("ck_paper_contents_valid_source_sha256"),
        ),
        CheckConstraint(
            "page_count IS NULL OR page_count >= 1",
            name=("ck_paper_contents_positive_page_count"),
        ),
        CheckConstraint(
            "text_page_count IS NULL OR text_page_count >= 0",
            name=("ck_paper_contents_nonnegative_text_page_count"),
        ),
        CheckConstraint(
            "page_count IS NULL "
            "OR text_page_count IS NULL "
            "OR text_page_count <= page_count",
            name=("ck_paper_contents_valid_text_page_count"),
        ),
        CheckConstraint(
            "content_type != 'full_text' OR ("
            "source_filename IS NOT NULL "
            "AND source_media_type IS NOT NULL "
            "AND source_sha256 IS NOT NULL "
            "AND access_basis IS NOT NULL "
            "AND page_count IS NOT NULL "
            "AND text_page_count IS NOT NULL "
            "AND extractor_name IS NOT NULL "
            "AND extractor_library_version IS NOT NULL"
            ")",
            name=("ck_paper_contents_full_text_has_provenance"),
        ),
        Index(
            "ix_paper_contents_checksum",
            "checksum",
        ),
        Index(
            "ix_paper_contents_source_sha256",
            "source_sha256",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    paper_id: Mapped[int] = mapped_column(
        ForeignKey(
            "papers.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    content_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )

    extraction_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )

    extracted_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    parser_version: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    checksum: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )

    source_filename: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    source_media_type: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    source_sha256: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )

    access_basis: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
    )

    page_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    text_page_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    extractor_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    extractor_library_version: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    extraction_error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
