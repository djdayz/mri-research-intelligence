from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from mrinsight.db.base import Base


class Topic(Base):
    """Explicit discovery topic and rules."""

    __tablename__ = "topics"

    __table_args__ = (
        UniqueConstraint("slug", name="uq_topics_slug"),
        CheckConstraint("length(slug) > 0", name="ck_topics_nonempty_slug"),
        CheckConstraint("length(query) > 0", name="ck_topics_nonempty_query"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    query: Mapped[str] = mapped_column(Text, nullable=False)
    rules: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    preferred_categories: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
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


class Subscription(Base):
    """User-configured discovery subscription."""

    __tablename__ = "subscriptions"

    __table_args__ = (
        CheckConstraint(
            "minimum_relevance_score >= 0 AND minimum_relevance_score <= 1",
            name="ck_subscriptions_relevance_score_range",
        ),
        CheckConstraint(
            "digest_cadence IN ('daily', 'weekly', 'monthly', 'manual')",
            name="ck_subscriptions_supported_digest_cadence",
        ),
        Index("ix_subscriptions_enabled", "enabled"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    discovery_query: Mapped[str] = mapped_column(Text, nullable=False)
    minimum_relevance_score: Mapped[float] = mapped_column(Float, nullable=False)
    preferred_categories: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    digest_cadence: Mapped[str] = mapped_column(String(32), nullable=False)
    delivery_destination: Mapped[str | None] = mapped_column(Text, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
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


class SubscriptionTopic(Base):
    """Join table between subscriptions and topics."""

    __tablename__ = "subscription_topics"

    __table_args__ = (
        UniqueConstraint(
            "subscription_id",
            "topic_id",
            name="uq_subscription_topics_subscription_topic",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    subscription_id: Mapped[int] = mapped_column(
        ForeignKey("subscriptions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    topic_id: Mapped[int] = mapped_column(
        ForeignKey("topics.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )


class DiscoveryRun(Base):
    """One discovery provider run."""

    __tablename__ = "discovery_runs"

    __table_args__ = (
        CheckConstraint(
            "status IN ('running', 'succeeded', 'failed')",
            name="ck_discovery_runs_supported_status",
        ),
        Index("ix_discovery_runs_subscription_status", "subscription_id", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    subscription_id: Mapped[int] = mapped_column(
        ForeignKey("subscriptions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    topic_id: Mapped[int | None] = mapped_column(
        ForeignKey("topics.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    provider: Mapped[str] = mapped_column(String(100), nullable=False)
    query: Mapped[str] = mapped_column(Text, nullable=False)
    from_publication_date: Mapped[date] = mapped_column(Date, nullable=False)
    until_publication_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )


class DiscoveryCandidateModel(Base):
    """Persisted candidate and outcome."""

    __tablename__ = "discovery_candidates"

    __table_args__ = (
        CheckConstraint(
            "status IN ('ingested', 'duplicate', 'skipped', 'failed')",
            name="ck_discovery_candidates_supported_status",
        ),
        CheckConstraint(
            "relevance_score IS NULL OR "
            "(relevance_score >= 0 AND relevance_score <= 1)",
            name="ck_discovery_candidates_relevance_score_range",
        ),
        Index("ix_discovery_candidates_run_status", "discovery_run_id", "status"),
        Index("ix_discovery_candidates_normalized_doi", "normalized_doi"),
        Index(
            "ix_discovery_candidates_title_date", "normalized_title", "publication_date"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    discovery_run_id: Mapped[int] = mapped_column(
        ForeignKey("discovery_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider: Mapped[str] = mapped_column(String(100), nullable=False)
    provider_record_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    doi: Mapped[str | None] = mapped_column(String(255), nullable=True)
    normalized_doi: Mapped[str | None] = mapped_column(String(255), nullable=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_title: Mapped[str] = mapped_column(Text, nullable=False)
    publication_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    paper_id: Mapped[int | None] = mapped_column(
        ForeignKey("papers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    relevance_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    rank_position: Mapped[int | None] = mapped_column(Integer, nullable=True)
    outcome_reason: Mapped[str | None] = mapped_column(Text, nullable=True)


class Digest(Base):
    """Rendered digest preview."""

    __tablename__ = "digests"

    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_digests_idempotency_key"),
        CheckConstraint(
            "status IN ('generated', 'failed')",
            name="ck_digests_supported_status",
        ),
        Index("ix_digests_subscription_date", "subscription_id", "digest_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    subscription_id: Mapped[int] = mapped_column(
        ForeignKey("subscriptions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    topic_id: Mapped[int | None] = mapped_column(
        ForeignKey("topics.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    digest_date: Mapped[date] = mapped_column(Date, nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    plain_text: Mapped[str] = mapped_column(Text, nullable=False)
    html: Mapped[str] = mapped_column(Text, nullable=False)
    selected_papers: Mapped[list[dict[str, object]]] = mapped_column(
        JSONB,
        nullable=False,
    )
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
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


class DigestDelivery(Base):
    """One digest delivery attempt."""

    __tablename__ = "digest_deliveries"

    __table_args__ = (
        UniqueConstraint(
            "idempotency_key", name="uq_digest_deliveries_idempotency_key"
        ),
        CheckConstraint(
            "status IN ('succeeded', 'failed')",
            name="ck_digest_deliveries_supported_status",
        ),
        Index("ix_digest_deliveries_digest_status", "digest_id", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    digest_id: Mapped[int] = mapped_column(
        ForeignKey("digests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider: Mapped[str] = mapped_column(String(100), nullable=False)
    destination: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
