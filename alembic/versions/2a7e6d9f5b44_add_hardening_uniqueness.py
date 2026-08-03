"""add hardening uniqueness

Revision ID: 2a7e6d9f5b44
Revises: 9f1c2e8d7a6b
Create Date: 2026-08-02 23:45:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2a7e6d9f5b44"
down_revision: str | Sequence[str] | None = "9f1c2e8d7a6b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""

    op.add_column(
        "digests",
        sa.Column("idempotency_key", sa.String(length=255), nullable=True),
    )
    op.execute(
        "UPDATE digests "
        "SET idempotency_key = 'legacy-digest:' || id::text "
        "WHERE idempotency_key IS NULL"
    )
    op.alter_column(
        "digests",
        "idempotency_key",
        existing_type=sa.String(length=255),
        nullable=False,
    )
    op.create_unique_constraint(
        "uq_digests_idempotency_key",
        "digests",
        ["idempotency_key"],
    )
    op.create_index(
        "uq_paper_analyses_success_cache_identity",
        "paper_analyses",
        [
            "paper_id",
            "paper_content_id",
            "analysis_scope",
            "content_checksum",
            "selected_evidence_checksum",
            "schema_version",
            "provider",
            "model",
            "prompt_version",
        ],
        unique=True,
        postgresql_where=sa.text("status = 'succeeded'"),
    )


def downgrade() -> None:
    """Downgrade schema."""

    op.drop_index(
        "uq_paper_analyses_success_cache_identity",
        table_name="paper_analyses",
        postgresql_where=sa.text("status = 'succeeded'"),
    )
    op.drop_constraint(
        "uq_digests_idempotency_key",
        "digests",
        type_="unique",
    )
    op.drop_column("digests", "idempotency_key")
