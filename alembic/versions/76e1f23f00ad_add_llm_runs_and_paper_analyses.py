"""add llm runs and paper analyses

Revision ID: 76e1f23f00ad
Revises: 4af4a9d74a1d
Create Date: 2026-08-02 21:10:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "76e1f23f00ad"
down_revision: str | Sequence[str] | None = "4af4a9d74a1d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""

    op.create_table(
        "llm_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(length=100), nullable=False),
        sa.Column("model", sa.String(length=100), nullable=False),
        sa.Column("prompt_version", sa.String(length=100), nullable=False),
        sa.Column("prompt_checksum", sa.String(length=64), nullable=False),
        sa.Column("schema_version", sa.String(length=100), nullable=False),
        sa.Column("input_checksum", sa.String(length=64), nullable=False),
        sa.Column(
            "selected_chunk_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("request_status", sa.String(length=32), nullable=False),
        sa.Column("repair_attempt_count", sa.Integer(), nullable=False),
        sa.Column("provider_request_id", sa.String(length=255), nullable=True),
        sa.Column("input_token_count", sa.Integer(), nullable=True),
        sa.Column("output_token_count", sa.Integer(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("estimated_cost", sa.Float(), nullable=True),
        sa.Column("error_category", sa.String(length=100), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "estimated_cost IS NULL OR estimated_cost >= 0",
            name="ck_llm_runs_nonnegative_estimated_cost",
        ),
        sa.CheckConstraint(
            "input_token_count IS NULL OR input_token_count >= 0",
            name="ck_llm_runs_nonnegative_input_tokens",
        ),
        sa.CheckConstraint(
            "latency_ms IS NULL OR latency_ms >= 0",
            name="ck_llm_runs_nonnegative_latency",
        ),
        sa.CheckConstraint(
            "output_token_count IS NULL OR output_token_count >= 0",
            name="ck_llm_runs_nonnegative_output_tokens",
        ),
        sa.CheckConstraint(
            "repair_attempt_count >= 0",
            name="ck_llm_runs_nonnegative_repair_attempts",
        ),
        sa.CheckConstraint(
            "request_status IN ('succeeded', 'failed', 'provider_failed')",
            name="ck_llm_runs_supported_request_status",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_llm_runs")),
    )

    op.create_table(
        "paper_analyses",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("paper_id", sa.Integer(), nullable=False),
        sa.Column("paper_content_id", sa.Integer(), nullable=False),
        sa.Column("analysis_scope", sa.String(length=32), nullable=False),
        sa.Column("content_checksum", sa.String(length=64), nullable=False),
        sa.Column("selected_evidence_checksum", sa.String(length=64), nullable=False),
        sa.Column("llm_run_id", sa.Integer(), nullable=True),
        sa.Column("schema_version", sa.String(length=100), nullable=False),
        sa.Column("provider", sa.String(length=100), nullable=False),
        sa.Column("model", sa.String(length=100), nullable=False),
        sa.Column("prompt_version", sa.String(length=100), nullable=False),
        sa.Column(
            "validated_analysis",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column(
            "validation_errors",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("relevance_version", sa.Text(), nullable=True),
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
            name="ck_paper_analyses_supported_scope",
        ),
        sa.CheckConstraint(
            "length(content_checksum) = 64",
            name="ck_paper_analyses_valid_content_checksum",
        ),
        sa.CheckConstraint(
            "length(selected_evidence_checksum) = 64",
            name="ck_paper_analyses_valid_selected_evidence_checksum",
        ),
        sa.CheckConstraint(
            "status IN ('succeeded', 'failed', 'ineligible')",
            name="ck_paper_analyses_supported_status",
        ),
        sa.ForeignKeyConstraint(
            ["llm_run_id"],
            ["llm_runs.id"],
            name=op.f("fk_paper_analyses_llm_run_id_llm_runs"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["paper_content_id"],
            ["paper_contents.id"],
            name=op.f("fk_paper_analyses_paper_content_id_paper_contents"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["paper_id"],
            ["papers.id"],
            name=op.f("fk_paper_analyses_paper_id_papers"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_paper_analyses")),
    )
    op.create_index(
        "ix_paper_analyses_cache_identity",
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
        unique=False,
    )
    op.create_index(
        op.f("ix_paper_analyses_llm_run_id"),
        "paper_analyses",
        ["llm_run_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_paper_analyses_paper_content_id"),
        "paper_analyses",
        ["paper_content_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_paper_analyses_paper_id"),
        "paper_analyses",
        ["paper_id"],
        unique=False,
    )
    op.create_index(
        "ix_paper_analyses_paper_status",
        "paper_analyses",
        ["paper_id", "status"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""

    op.drop_index(
        "ix_paper_analyses_paper_status",
        table_name="paper_analyses",
    )
    op.drop_index(
        "ix_paper_analyses_cache_identity",
        table_name="paper_analyses",
    )
    op.drop_index(
        op.f("ix_paper_analyses_paper_id"),
        table_name="paper_analyses",
    )
    op.drop_index(
        op.f("ix_paper_analyses_paper_content_id"),
        table_name="paper_analyses",
    )
    op.drop_index(
        op.f("ix_paper_analyses_llm_run_id"),
        table_name="paper_analyses",
    )
    op.drop_table("paper_analyses")
    op.drop_table("llm_runs")
