"""add delivery retry metadata

Revision ID: 5d3b9a1c4e22
Revises: 2a7e6d9f5b44
Create Date: 2026-08-03 00:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5d3b9a1c4e22"
down_revision: str | Sequence[str] | None = "2a7e6d9f5b44"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""

    op.add_column(
        "digest_deliveries",
        sa.Column("provider_response_id", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "digest_deliveries",
        sa.Column(
            "attempt_count",
            sa.Integer(),
            server_default="1",
            nullable=False,
        ),
    )
    op.add_column(
        "digest_deliveries",
        sa.Column(
            "retryable",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
    )
    op.add_column(
        "digest_deliveries",
        sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "digest_deliveries",
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "digest_deliveries",
        sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.execute(
        "UPDATE digest_deliveries "
        "SET delivered_at = completed_at "
        "WHERE status = 'succeeded' AND delivered_at IS NULL"
    )
    op.execute(
        "UPDATE digest_deliveries "
        "SET failed_at = completed_at "
        "WHERE status = 'failed' AND failed_at IS NULL"
    )
    op.create_check_constraint(
        "ck_digest_deliveries_positive_attempt_count",
        "digest_deliveries",
        "attempt_count >= 1",
    )
    op.create_check_constraint(
        "ck_digest_deliveries_valid_terminal_timestamps",
        "digest_deliveries",
        "("
        "status = 'succeeded' "
        "AND delivered_at IS NOT NULL "
        "AND failed_at IS NULL"
        ") OR ("
        "status = 'failed' "
        "AND failed_at IS NOT NULL "
        "AND delivered_at IS NULL"
        ")",
    )
    op.create_index(
        "ix_digest_deliveries_retry_due",
        "digest_deliveries",
        ["provider", "next_retry_at"],
        unique=False,
        postgresql_where=sa.text("retryable IS TRUE"),
    )
    op.create_index(
        "uq_digest_deliveries_success_digest_provider",
        "digest_deliveries",
        ["digest_id", "provider"],
        unique=True,
        postgresql_where=sa.text("status = 'succeeded'"),
    )
    op.alter_column(
        "digest_deliveries",
        "attempt_count",
        server_default=None,
    )
    op.alter_column(
        "digest_deliveries",
        "retryable",
        server_default=None,
    )


def downgrade() -> None:
    """Downgrade schema."""

    op.drop_index(
        "uq_digest_deliveries_success_digest_provider",
        table_name="digest_deliveries",
        postgresql_where=sa.text("status = 'succeeded'"),
    )
    op.drop_index(
        "ix_digest_deliveries_retry_due",
        table_name="digest_deliveries",
        postgresql_where=sa.text("retryable IS TRUE"),
    )
    op.drop_constraint(
        "ck_digest_deliveries_valid_terminal_timestamps",
        "digest_deliveries",
        type_="check",
    )
    op.drop_constraint(
        "ck_digest_deliveries_positive_attempt_count",
        "digest_deliveries",
        type_="check",
    )
    op.drop_column("digest_deliveries", "failed_at")
    op.drop_column("digest_deliveries", "delivered_at")
    op.drop_column("digest_deliveries", "next_retry_at")
    op.drop_column("digest_deliveries", "retryable")
    op.drop_column("digest_deliveries", "attempt_count")
    op.drop_column("digest_deliveries", "provider_response_id")
