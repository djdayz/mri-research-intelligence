from datetime import date, datetime

from sqlalchemy import Date, DateTime, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from mrinsight.db.base import Base


class Paper(Base):
    """Bibliographic metadata for a scientific paper"""

    __tablename__ = "papers"

    __table_args__ = (
        UniqueConstraint(
            "normalized_doi",
            name="uq_papers_normalized_doi",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    doi: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    normalized_doi: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    title: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    normalized_title: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        index=True,
    )

    abstract: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    publication_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    source_url: Mapped[str | None] = mapped_column(
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
