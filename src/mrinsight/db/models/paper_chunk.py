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


class PaperChunk(Base):
    """One bounded evidence unit from scientific paper content."""

    __tablename__ = "paper_chunks"

    __table_args__ = (
        UniqueConstraint(
            "paper_content_id",
            "sequence_number",
            name=("uq_paper_chunks_paper_content_id_sequence_number"),
        ),
        CheckConstraint(
            "section IN ("
            "'abstract', "
            "'background', "
            "'introduction', "
            "'methods', "
            "'results', "
            "'discussion', "
            "'limitations', "
            "'conclusion', "
            "'references', "
            "'other'"
            ")",
            name="ck_paper_chunks_supported_section",
        ),
        CheckConstraint(
            "sequence_number >= 1",
            name="ck_paper_chunks_positive_sequence",
        ),
        CheckConstraint(
            "start_char >= 0 AND end_char > start_char",
            name="ck_paper_chunks_valid_character_range",
        ),
        CheckConstraint(
            "paragraph_start_sequence >= 1 "
            "AND paragraph_end_sequence "
            ">= paragraph_start_sequence",
            name="ck_paper_chunks_valid_paragraph_range",
        ),
        CheckConstraint(
            "token_count >= 1",
            name="ck_paper_chunks_positive_token_count",
        ),
        CheckConstraint(
            "page_number IS NULL OR page_number >= 1",
            name="ck_paper_chunks_positive_page_number",
        ),
        CheckConstraint(
            "length(text) > 0",
            name="ck_paper_chunks_nonempty_text",
        ),
        Index(
            "ix_paper_chunks_paper_content_id",
            "paper_content_id",
        ),
        Index(
            "ix_paper_chunks_paper_id_section",
            "paper_id",
            "section",
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
    )

    paper_content_id: Mapped[int] = mapped_column(
        ForeignKey(
            "paper_contents.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    section: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )

    heading: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    sequence_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    start_char: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    end_char: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    paragraph_start_sequence: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    paragraph_end_sequence: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    token_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    page_number: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    chunker_version: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
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
