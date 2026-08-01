from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from mrinsight.db.base import Base


class PaperContentPage(Base):
    """One text-bearing page from extracted full text."""

    __tablename__ = "paper_content_pages"

    __table_args__ = (
        UniqueConstraint(
            "paper_content_id",
            "page_number",
            name=("uq_paper_content_pages_content_id_page_number"),
        ),
        CheckConstraint(
            "page_number >= 1",
            name=("ck_paper_content_pages_positive_page_number"),
        ),
        CheckConstraint(
            "start_char >= 0 AND end_char > start_char",
            name=("ck_paper_content_pages_valid_character_range"),
        ),
        CheckConstraint(
            "length(text) > 0",
            name=("ck_paper_content_pages_nonempty_text"),
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    paper_content_id: Mapped[int] = mapped_column(
        ForeignKey(
            "paper_contents.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    page_number: Mapped[int] = mapped_column(
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

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
