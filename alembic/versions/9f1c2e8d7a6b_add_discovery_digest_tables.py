"""add discovery digest tables

Revision ID: 9f1c2e8d7a6b
Revises: b3d21e9c4c8a
Create Date: 2026-08-02 23:10:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "9f1c2e8d7a6b"
down_revision: str | Sequence[str] | None = "b3d21e9c4c8a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SEEDED_TOPICS: tuple[dict[str, object], ...] = (
    {
        "slug": "mri-cvr-mapping",
        "name": "MRI CVR mapping",
        "description": "Cerebrovascular reactivity mapping with MRI.",
        "query": "MRI cerebrovascular reactivity CVR mapping BOLD",
        "rules": {"required_any": ["mri", "cvr"], "focus": "mapping"},
        "preferred_categories": ["mri", "cvr"],
    },
    {
        "slug": "cvr-methodology",
        "name": "CVR methodology",
        "description": "Methods and validation for CVR measurement.",
        "query": "cerebrovascular reactivity methodology validation MRI",
        "rules": {"required_any": ["cvr"], "focus": "methods"},
        "preferred_categories": ["cvr"],
    },
    {
        "slug": "mri-machine-learning",
        "name": "MRI machine learning",
        "description": "Machine-learning methods for MRI research.",
        "query": "MRI machine learning model validation",
        "rules": {"required_any": ["mri", "machine_learning"], "focus": "ml"},
        "preferred_categories": ["mri", "machine_learning"],
    },
    {
        "slug": "mri-deep-learning",
        "name": "MRI deep learning",
        "description": "Deep-learning MRI methods and validation.",
        "query": "MRI deep learning neural network validation",
        "rules": {"required_any": ["mri", "deep_learning"], "focus": "dl"},
        "preferred_categories": ["mri", "machine_learning"],
    },
    {
        "slug": "mri-reconstruction",
        "name": "MRI reconstruction",
        "description": "MRI reconstruction algorithms and evaluation.",
        "query": "MRI reconstruction accelerated imaging validation",
        "rules": {"required_any": ["mri_reconstruction"], "focus": "reconstruction"},
        "preferred_categories": ["reconstruction", "mri"],
    },
    {
        "slug": "trustworthy-mri-ai",
        "name": "Trustworthy MRI AI",
        "description": "Trustworthy, reproducible, and validated MRI AI.",
        "query": "trustworthy reproducible MRI artificial intelligence validation",
        "rules": {"required_any": ["mri"], "focus": "trustworthiness"},
        "preferred_categories": ["mri", "machine_learning"],
    },
    {
        "slug": "uncertainty-medical-imaging",
        "name": "Uncertainty in medical imaging",
        "description": "Uncertainty estimation and reporting in medical imaging.",
        "query": "uncertainty estimation medical imaging MRI validation",
        "rules": {"required_any": ["mri"], "focus": "uncertainty"},
        "preferred_categories": ["mri"],
    },
)


def upgrade() -> None:
    """Upgrade schema."""

    op.create_table(
        "topics",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("rules", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "preferred_categories",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("enabled", sa.Boolean(), nullable=False),
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
        sa.CheckConstraint("length(query) > 0", name="ck_topics_nonempty_query"),
        sa.CheckConstraint("length(slug) > 0", name="ck_topics_nonempty_slug"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_topics")),
        sa.UniqueConstraint("slug", name="uq_topics_slug"),
    )
    op.create_table(
        "subscriptions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("discovery_query", sa.Text(), nullable=False),
        sa.Column("minimum_relevance_score", sa.Float(), nullable=False),
        sa.Column(
            "preferred_categories",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("digest_cadence", sa.String(length=32), nullable=False),
        sa.Column("delivery_destination", sa.Text(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("last_processed_at", sa.DateTime(timezone=True), nullable=True),
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
            "digest_cadence IN ('daily', 'weekly', 'monthly', 'manual')",
            name="ck_subscriptions_supported_digest_cadence",
        ),
        sa.CheckConstraint(
            "minimum_relevance_score >= 0 AND minimum_relevance_score <= 1",
            name="ck_subscriptions_relevance_score_range",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_subscriptions")),
    )
    op.create_index(
        "ix_subscriptions_enabled",
        "subscriptions",
        ["enabled"],
        unique=False,
    )
    op.create_table(
        "subscription_topics",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("subscription_id", sa.Integer(), nullable=False),
        sa.Column("topic_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["subscription_id"],
            ["subscriptions.id"],
            name=op.f("fk_subscription_topics_subscription_id_subscriptions"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["topic_id"],
            ["topics.id"],
            name=op.f("fk_subscription_topics_topic_id_topics"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_subscription_topics")),
        sa.UniqueConstraint(
            "subscription_id",
            "topic_id",
            name="uq_subscription_topics_subscription_topic",
        ),
    )
    op.create_index(
        op.f("ix_subscription_topics_subscription_id"),
        "subscription_topics",
        ["subscription_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_subscription_topics_topic_id"),
        "subscription_topics",
        ["topic_id"],
        unique=False,
    )
    op.create_table(
        "discovery_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("subscription_id", sa.Integer(), nullable=False),
        sa.Column("topic_id", sa.Integer(), nullable=True),
        sa.Column("provider", sa.String(length=100), nullable=False),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("from_publication_date", sa.Date(), nullable=False),
        sa.Column("until_publication_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('running', 'succeeded', 'failed')",
            name="ck_discovery_runs_supported_status",
        ),
        sa.ForeignKeyConstraint(
            ["subscription_id"],
            ["subscriptions.id"],
            name=op.f("fk_discovery_runs_subscription_id_subscriptions"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["topic_id"],
            ["topics.id"],
            name=op.f("fk_discovery_runs_topic_id_topics"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_discovery_runs")),
    )
    op.create_index(
        op.f("ix_discovery_runs_subscription_id"),
        "discovery_runs",
        ["subscription_id"],
        unique=False,
    )
    op.create_index(
        "ix_discovery_runs_subscription_status",
        "discovery_runs",
        ["subscription_id", "status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_discovery_runs_topic_id"),
        "discovery_runs",
        ["topic_id"],
        unique=False,
    )
    op.create_table(
        "discovery_candidates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("discovery_run_id", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(length=100), nullable=False),
        sa.Column("provider_record_id", sa.String(length=255), nullable=True),
        sa.Column("doi", sa.String(length=255), nullable=True),
        sa.Column("normalized_doi", sa.String(length=255), nullable=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("normalized_title", sa.Text(), nullable=False),
        sa.Column("publication_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("paper_id", sa.Integer(), nullable=True),
        sa.Column("relevance_score", sa.Float(), nullable=True),
        sa.Column("rank_position", sa.Integer(), nullable=True),
        sa.Column("outcome_reason", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "relevance_score IS NULL OR "
            "(relevance_score >= 0 AND relevance_score <= 1)",
            name="ck_discovery_candidates_relevance_score_range",
        ),
        sa.CheckConstraint(
            "status IN ('ingested', 'duplicate', 'skipped', 'failed')",
            name="ck_discovery_candidates_supported_status",
        ),
        sa.ForeignKeyConstraint(
            ["discovery_run_id"],
            ["discovery_runs.id"],
            name=op.f("fk_discovery_candidates_discovery_run_id_discovery_runs"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["paper_id"],
            ["papers.id"],
            name=op.f("fk_discovery_candidates_paper_id_papers"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_discovery_candidates")),
    )
    op.create_index(
        op.f("ix_discovery_candidates_discovery_run_id"),
        "discovery_candidates",
        ["discovery_run_id"],
        unique=False,
    )
    op.create_index(
        "ix_discovery_candidates_normalized_doi",
        "discovery_candidates",
        ["normalized_doi"],
        unique=False,
    )
    op.create_index(
        op.f("ix_discovery_candidates_paper_id"),
        "discovery_candidates",
        ["paper_id"],
        unique=False,
    )
    op.create_index(
        "ix_discovery_candidates_run_status",
        "discovery_candidates",
        ["discovery_run_id", "status"],
        unique=False,
    )
    op.create_index(
        "ix_discovery_candidates_title_date",
        "discovery_candidates",
        ["normalized_title", "publication_date"],
        unique=False,
    )
    op.create_table(
        "digests",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("subscription_id", sa.Integer(), nullable=False),
        sa.Column("topic_id", sa.Integer(), nullable=True),
        sa.Column("digest_date", sa.Date(), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("plain_text", sa.Text(), nullable=False),
        sa.Column("html", sa.Text(), nullable=False),
        sa.Column(
            "selected_papers",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("error", sa.Text(), nullable=True),
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
            "status IN ('generated', 'failed')",
            name="ck_digests_supported_status",
        ),
        sa.ForeignKeyConstraint(
            ["subscription_id"],
            ["subscriptions.id"],
            name=op.f("fk_digests_subscription_id_subscriptions"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["topic_id"],
            ["topics.id"],
            name=op.f("fk_digests_topic_id_topics"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_digests")),
    )
    op.create_index(
        op.f("ix_digests_subscription_id"),
        "digests",
        ["subscription_id"],
        unique=False,
    )
    op.create_index(
        "ix_digests_subscription_date",
        "digests",
        ["subscription_id", "digest_date"],
        unique=False,
    )
    op.create_index(
        op.f("ix_digests_topic_id"),
        "digests",
        ["topic_id"],
        unique=False,
    )
    op.create_table(
        "digest_deliveries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("digest_id", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(length=100), nullable=False),
        sa.Column("destination", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('succeeded', 'failed')",
            name="ck_digest_deliveries_supported_status",
        ),
        sa.ForeignKeyConstraint(
            ["digest_id"],
            ["digests.id"],
            name=op.f("fk_digest_deliveries_digest_id_digests"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_digest_deliveries")),
        sa.UniqueConstraint(
            "idempotency_key",
            name="uq_digest_deliveries_idempotency_key",
        ),
    )
    op.create_index(
        op.f("ix_digest_deliveries_digest_id"),
        "digest_deliveries",
        ["digest_id"],
        unique=False,
    )
    op.create_index(
        "ix_digest_deliveries_digest_status",
        "digest_deliveries",
        ["digest_id", "status"],
        unique=False,
    )

    topics_table = sa.table(
        "topics",
        sa.column("slug", sa.String),
        sa.column("name", sa.String),
        sa.column("description", sa.Text),
        sa.column("query", sa.Text),
        sa.column("rules", postgresql.JSONB),
        sa.column("preferred_categories", postgresql.JSONB),
        sa.column("enabled", sa.Boolean),
    )
    op.bulk_insert(
        topics_table,
        [
            {
                **topic,
                "enabled": True,
            }
            for topic in SEEDED_TOPICS
        ],
    )


def downgrade() -> None:
    """Downgrade schema."""

    op.drop_index("ix_digest_deliveries_digest_status", table_name="digest_deliveries")
    op.drop_index(
        op.f("ix_digest_deliveries_digest_id"), table_name="digest_deliveries"
    )
    op.drop_table("digest_deliveries")
    op.drop_index(op.f("ix_digests_topic_id"), table_name="digests")
    op.drop_index("ix_digests_subscription_date", table_name="digests")
    op.drop_index(op.f("ix_digests_subscription_id"), table_name="digests")
    op.drop_table("digests")
    op.drop_index(
        "ix_discovery_candidates_title_date", table_name="discovery_candidates"
    )
    op.drop_index(
        "ix_discovery_candidates_run_status", table_name="discovery_candidates"
    )
    op.drop_index(
        op.f("ix_discovery_candidates_paper_id"), table_name="discovery_candidates"
    )
    op.drop_index(
        "ix_discovery_candidates_normalized_doi",
        table_name="discovery_candidates",
    )
    op.drop_index(
        op.f("ix_discovery_candidates_discovery_run_id"),
        table_name="discovery_candidates",
    )
    op.drop_table("discovery_candidates")
    op.drop_index(op.f("ix_discovery_runs_topic_id"), table_name="discovery_runs")
    op.drop_index("ix_discovery_runs_subscription_status", table_name="discovery_runs")
    op.drop_index(
        op.f("ix_discovery_runs_subscription_id"),
        table_name="discovery_runs",
    )
    op.drop_table("discovery_runs")
    op.drop_index(
        op.f("ix_subscription_topics_topic_id"),
        table_name="subscription_topics",
    )
    op.drop_index(
        op.f("ix_subscription_topics_subscription_id"),
        table_name="subscription_topics",
    )
    op.drop_table("subscription_topics")
    op.drop_index("ix_subscriptions_enabled", table_name="subscriptions")
    op.drop_table("subscriptions")
    op.drop_table("topics")
