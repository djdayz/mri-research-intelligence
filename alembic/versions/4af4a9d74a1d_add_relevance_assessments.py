"""add relevance assessments

Revision ID: 4af4a9d74a1d
Revises: 8f8d1c2e7b90
Create Date: 2026-08-02 18:20:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "4af4a9d74a1d"
down_revision: str | Sequence[str] | None = "8f8d1c2e7b90"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""

    op.create_table(
        "paper_relevance_assessments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("paper_id", sa.Integer(), nullable=False),
        sa.Column("paper_content_id", sa.Integer(), nullable=False),
        sa.Column("analysis_scope", sa.String(length=32), nullable=False),
        sa.Column("content_checksum", sa.String(length=64), nullable=False),
        sa.Column("rule_score", sa.Float(), nullable=False),
        sa.Column("normalized_score", sa.Float(), nullable=False),
        sa.Column("rule_label", sa.String(length=32), nullable=False),
        sa.Column(
            "category_scores",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "matched_concepts",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "matched_terms",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "supporting_locations",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("rule_version", sa.String(length=100), nullable=False),
        sa.Column("ontology_version", sa.String(length=100), nullable=False),
        sa.Column("model_version", sa.String(length=100), nullable=False),
        sa.Column("tfidf_label", sa.String(length=100), nullable=True),
        sa.Column("tfidf_confidence", sa.Float(), nullable=True),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "analysis_scope IN ('abstract_only', 'full_text')",
            name="ck_paper_relevance_assessments_supported_scope",
        ),
        sa.CheckConstraint(
            "length(content_checksum) = 64",
            name="ck_paper_relevance_assessments_valid_content_checksum",
        ),
        sa.CheckConstraint(
            "normalized_score >= 0 AND normalized_score <= 1",
            name="ck_paper_relevance_assessments_normalized_score_range",
        ),
        sa.CheckConstraint(
            "rule_label IN ('high', 'medium', 'low', 'not_relevant')",
            name="ck_paper_relevance_assessments_supported_label",
        ),
        sa.CheckConstraint(
            "rule_score >= 0",
            name="ck_paper_relevance_assessments_nonnegative_rule_score",
        ),
        sa.CheckConstraint(
            "tfidf_confidence IS NULL "
            "OR (tfidf_confidence >= 0 AND tfidf_confidence <= 1)",
            name="ck_paper_relevance_assessments_tfidf_confidence_range",
        ),
        sa.ForeignKeyConstraint(
            ["paper_content_id"],
            ["paper_contents.id"],
            name=op.f("fk_paper_relevance_assessments_paper_content_id_paper_contents"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["paper_id"],
            ["papers.id"],
            name=op.f("fk_paper_relevance_assessments_paper_id_papers"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name=op.f("pk_paper_relevance_assessments"),
        ),
        sa.UniqueConstraint(
            "paper_id",
            "paper_content_id",
            "analysis_scope",
            "content_checksum",
            "rule_version",
            "ontology_version",
            "model_version",
            name="uq_paper_relevance_assessments_cache_identity",
        ),
    )
    op.create_index(
        op.f("ix_paper_relevance_assessments_paper_content_id"),
        "paper_relevance_assessments",
        ["paper_content_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_paper_relevance_assessments_paper_id"),
        "paper_relevance_assessments",
        ["paper_id"],
        unique=False,
    )
    op.create_index(
        "ix_paper_relevance_assessments_paper_label",
        "paper_relevance_assessments",
        ["paper_id", "rule_label"],
        unique=False,
    )
    op.create_index(
        "ix_paper_relevance_assessments_rule_label_score",
        "paper_relevance_assessments",
        ["rule_label", "normalized_score"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""

    op.drop_index(
        "ix_paper_relevance_assessments_rule_label_score",
        table_name="paper_relevance_assessments",
    )
    op.drop_index(
        "ix_paper_relevance_assessments_paper_label",
        table_name="paper_relevance_assessments",
    )
    op.drop_index(
        op.f("ix_paper_relevance_assessments_paper_id"),
        table_name="paper_relevance_assessments",
    )
    op.drop_index(
        op.f("ix_paper_relevance_assessments_paper_content_id"),
        table_name="paper_relevance_assessments",
    )
    op.drop_table("paper_relevance_assessments")
