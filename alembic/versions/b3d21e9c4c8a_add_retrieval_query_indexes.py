"""add retrieval query indexes

Revision ID: b3d21e9c4c8a
Revises: 76e1f23f00ad
Create Date: 2026-08-02 22:30:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b3d21e9c4c8a"
down_revision: str | Sequence[str] | None = "76e1f23f00ad"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""

    op.create_index(
        "ix_papers_publication_date",
        "papers",
        ["publication_date"],
        unique=False,
    )
    op.create_index(
        "ix_papers_created_at",
        "papers",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        "ix_papers_ingestion_source",
        "papers",
        ["ingestion_source"],
        unique=False,
    )
    op.create_index(
        "ix_paper_contents_type_status_paper",
        "paper_contents",
        ["content_type", "extraction_status", "paper_id"],
        unique=False,
    )
    op.create_index(
        "ix_paper_relevance_assessments_category_scores_gin",
        "paper_relevance_assessments",
        ["category_scores"],
        unique=False,
        postgresql_using="gin",
    )
    op.create_index(
        "ix_paper_analyses_status_scope_paper",
        "paper_analyses",
        ["status", "analysis_scope", "paper_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""

    op.drop_index(
        "ix_paper_analyses_status_scope_paper",
        table_name="paper_analyses",
    )
    op.drop_index(
        "ix_paper_relevance_assessments_category_scores_gin",
        table_name="paper_relevance_assessments",
    )
    op.drop_index(
        "ix_paper_contents_type_status_paper",
        table_name="paper_contents",
    )
    op.drop_index(
        "ix_papers_ingestion_source",
        table_name="papers",
    )
    op.drop_index(
        "ix_papers_created_at",
        table_name="papers",
    )
    op.drop_index(
        "ix_papers_publication_date",
        table_name="papers",
    )
