from dataclasses import asdict
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from mrinsight.discovery import (
    DigestCadence,
    DigestPaper,
    DigestRunResult,
    NewSubscription,
    StoredDigest,
    StoredSubscription,
    StoredTopic,
)


class TopicResponse(BaseModel):
    """Public topic response."""

    model_config = ConfigDict(extra="forbid")

    id: int
    slug: str
    name: str
    description: str
    query: str
    rules: dict[str, Any]
    preferred_categories: tuple[str, ...]
    enabled: bool

    @classmethod
    def from_stored(cls, topic: StoredTopic) -> "TopicResponse":
        """Create response from stored topic."""

        return cls(
            id=topic.id,
            slug=topic.slug,
            name=topic.name,
            description=topic.description,
            query=topic.query,
            rules=topic.rules,
            preferred_categories=topic.preferred_categories,
            enabled=topic.enabled,
        )


class SubscriptionCreateRequest(BaseModel):
    """Request body for creating a subscription."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(min_length=1)
    discovery_query: str = Field(min_length=1)
    topic_ids: tuple[int, ...] = Field(min_length=1)
    minimum_relevance_score: float = Field(default=0.0, ge=0, le=1)
    preferred_categories: tuple[str, ...] = ()
    digest_cadence: DigestCadence = DigestCadence.WEEKLY
    delivery_destination: str | None = None
    enabled: bool = True

    def to_new_subscription(self) -> NewSubscription:
        """Return domain subscription."""

        return NewSubscription(
            name=self.name,
            discovery_query=self.discovery_query,
            topic_ids=self.topic_ids,
            minimum_relevance_score=self.minimum_relevance_score,
            preferred_categories=self.preferred_categories,
            digest_cadence=self.digest_cadence,
            delivery_destination=self.delivery_destination,
            enabled=self.enabled,
        )


class SubscriptionResponse(BaseModel):
    """Public subscription response."""

    model_config = ConfigDict(extra="forbid")

    id: int
    name: str
    discovery_query: str
    topic_ids: tuple[int, ...]
    topics: tuple[TopicResponse, ...]
    minimum_relevance_score: float
    preferred_categories: tuple[str, ...]
    digest_cadence: DigestCadence
    delivery_destination: str | None
    enabled: bool
    last_processed_at: datetime | None
    created_at: datetime | None
    updated_at: datetime | None

    @classmethod
    def from_stored(
        cls,
        subscription: StoredSubscription,
    ) -> "SubscriptionResponse":
        """Create response from stored subscription."""

        return cls(
            id=subscription.id,
            name=subscription.name,
            discovery_query=subscription.discovery_query,
            topic_ids=subscription.topic_ids,
            topics=tuple(
                TopicResponse.from_stored(topic) for topic in subscription.topics
            ),
            minimum_relevance_score=subscription.minimum_relevance_score,
            preferred_categories=subscription.preferred_categories,
            digest_cadence=subscription.digest_cadence,
            delivery_destination=subscription.delivery_destination,
            enabled=subscription.enabled,
            last_processed_at=subscription.last_processed_at,
            created_at=subscription.created_at,
            updated_at=subscription.updated_at,
        )


class DigestPreviewRequest(BaseModel):
    """Request body for manual digest preview."""

    model_config = ConfigDict(extra="forbid")

    period_start: date | None = None
    period_end: date | None = None
    rows: int = Field(default=20, ge=1, le=100)


class DigestPaperResponse(BaseModel):
    """Public selected digest paper."""

    model_config = ConfigDict(extra="forbid")

    paper_id: int
    doi: str | None
    title: str
    journal: str | None
    publication_date: date | None
    relevance_score: float | None
    analysis_scope: str | None
    concise_summary: str
    methodology_highlights: tuple[str, ...]
    main_results: tuple[str, ...]
    limitations: tuple[str, ...]
    link: str | None
    provenance: str
    ranking_explanation: str

    @classmethod
    def from_digest_paper(cls, paper: DigestPaper) -> "DigestPaperResponse":
        """Create response from digest paper."""

        return cls(**asdict(paper))


class DigestResponse(BaseModel):
    """Public digest response."""

    model_config = ConfigDict(extra="forbid")

    id: int
    subscription_id: int
    topic_id: int | None
    digest_date: date
    period_start: date
    period_end: date
    status: str
    title: str
    plain_text: str
    html: str
    selected_papers: tuple[DigestPaperResponse, ...]
    error: str | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_stored(cls, digest: StoredDigest) -> "DigestResponse":
        """Create response from stored digest."""

        return cls(
            id=digest.id,
            subscription_id=digest.subscription_id,
            topic_id=digest.topic_id,
            digest_date=digest.digest_date,
            period_start=digest.period_start,
            period_end=digest.period_end,
            status=digest.status.value,
            title=digest.title,
            plain_text=digest.plain_text,
            html=digest.html,
            selected_papers=tuple(
                DigestPaperResponse.from_digest_paper(paper)
                for paper in digest.selected_papers
            ),
            error=digest.error,
            created_at=digest.created_at,
            updated_at=digest.updated_at,
        )


class DigestPreviewResponse(BaseModel):
    """Public manual digest preview workflow response."""

    model_config = ConfigDict(extra="forbid")

    subscription: SubscriptionResponse
    discovery_run_ids: tuple[int, ...]
    candidate_count: int
    digest: DigestResponse
    delivery_id: int
    delivery_status: str

    @classmethod
    def from_result(cls, result: DigestRunResult) -> "DigestPreviewResponse":
        """Create response from workflow result."""

        return cls(
            subscription=SubscriptionResponse.from_stored(result.subscription),
            discovery_run_ids=tuple(run.id for run in result.discovery_runs),
            candidate_count=len(result.candidates),
            digest=DigestResponse.from_stored(result.digest),
            delivery_id=result.delivery.id,
            delivery_status=result.delivery.status.value,
        )
