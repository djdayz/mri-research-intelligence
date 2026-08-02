from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from mrinsight.db.base import Base


class PaperAnalysis(Base):
    """Validated or failed structured analysis for one paper content source."""

    __tablename__ = "paper_analyses"

    __table_args__ = (
        Index(
            "ix_paper_analyses_cache_identity",
            "paper_id",
            "paper_content_id",
            "analysis_scope",
            "content_checksum",
            "selected_evidence_checksum",
            "schema_version",
            "provider",
            "model",
            "prompt_version",
        ),
        CheckConstraint(
            "analysis_scope IN ('abstract_only', 'full_text')",
            name="ck_paper_analyses_supported_scope",
        ),
        CheckConstraint(
            "status IN ('succeeded', 'failed', 'ineligible')",
            name="ck_paper_analyses_supported_status",
        ),
        CheckConstraint(
            "length(content_checksum) = 64",
            name="ck_paper_analyses_valid_content_checksum",
        ),
        CheckConstraint(
            "length(selected_evidence_checksum) = 64",
            name="ck_paper_analyses_valid_selected_evidence_checksum",
        ),
        Index(
            "ix_paper_analyses_paper_status",
            "paper_id",
            "status",
        ),
        Index(
            "ix_paper_analyses_status_scope_paper",
            "status",
            "analysis_scope",
            "paper_id",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    paper_id: Mapped[int] = mapped_column(
        ForeignKey("papers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    paper_content_id: Mapped[int] = mapped_column(
        ForeignKey("paper_contents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    analysis_scope: Mapped[str] = mapped_column(String(32), nullable=False)
    content_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    selected_evidence_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    llm_run_id: Mapped[int | None] = mapped_column(
        ForeignKey("llm_runs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    schema_version: Mapped[str] = mapped_column(String(100), nullable=False)
    provider: Mapped[str] = mapped_column(String(100), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(100), nullable=False)
    validated_analysis: Mapped[dict[str, object] | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    validation_errors: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    relevance_version: Mapped[str | None] = mapped_column(Text, nullable=True)
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
