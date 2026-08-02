from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from mrinsight.db.base import Base


class PaperRelevanceAssessment(Base):
    """Versioned relevance assessment for one selected evidence source."""

    __tablename__ = "paper_relevance_assessments"

    __table_args__ = (
        UniqueConstraint(
            "paper_id",
            "paper_content_id",
            "analysis_scope",
            "content_checksum",
            "rule_version",
            "ontology_version",
            "model_version",
            name="uq_paper_relevance_assessments_cache_identity",
        ),
        CheckConstraint(
            "analysis_scope IN ('abstract_only', 'full_text')",
            name="ck_paper_relevance_assessments_supported_scope",
        ),
        CheckConstraint(
            "rule_label IN ('high', 'medium', 'low', 'not_relevant')",
            name="ck_paper_relevance_assessments_supported_label",
        ),
        CheckConstraint(
            "rule_score >= 0",
            name="ck_paper_relevance_assessments_nonnegative_rule_score",
        ),
        CheckConstraint(
            "normalized_score >= 0 AND normalized_score <= 1",
            name="ck_paper_relevance_assessments_normalized_score_range",
        ),
        CheckConstraint(
            "tfidf_confidence IS NULL "
            "OR (tfidf_confidence >= 0 AND tfidf_confidence <= 1)",
            name="ck_paper_relevance_assessments_tfidf_confidence_range",
        ),
        CheckConstraint(
            "length(content_checksum) = 64",
            name="ck_paper_relevance_assessments_valid_content_checksum",
        ),
        Index(
            "ix_paper_relevance_assessments_paper_label",
            "paper_id",
            "rule_label",
        ),
        Index(
            "ix_paper_relevance_assessments_rule_label_score",
            "rule_label",
            "normalized_score",
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

    paper_content_id: Mapped[int] = mapped_column(
        ForeignKey(
            "paper_contents.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    analysis_scope: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )

    content_checksum: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    rule_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    normalized_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    rule_label: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )

    category_scores: Mapped[dict[str, float]] = mapped_column(
        JSONB,
        nullable=False,
    )

    matched_concepts: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
    )

    matched_terms: Mapped[list[dict[str, object]]] = mapped_column(
        JSONB,
        nullable=False,
    )

    supporting_locations: Mapped[list[dict[str, object]]] = mapped_column(
        JSONB,
        nullable=False,
    )

    rule_version: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    ontology_version: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    model_version: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    tfidf_label: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    tfidf_confidence: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    explanation: Mapped[str] = mapped_column(
        Text,
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
