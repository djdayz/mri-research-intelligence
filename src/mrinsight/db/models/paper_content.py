from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
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
            "AND checksum IS NOT NULL"
            ") OR extraction_status = 'failed'",
            name=("ck_paper_contents_successful_content_has_text"),
        ),
        Index(
            "ix_paper_contents_checksum",
            "checksum",
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
