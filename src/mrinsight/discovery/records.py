from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum


class DigestCadence(StrEnum):
    """Supported digest cadences."""

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    MANUAL = "manual"


class DiscoveryRunStatus(StrEnum):
    """Persisted discovery run status."""

    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class DiscoveryCandidateStatus(StrEnum):
    """Persisted outcome for one provider candidate."""

    INGESTED = "ingested"
    DUPLICATE = "duplicate"
    SKIPPED = "skipped"
    FAILED = "failed"


class DigestStatus(StrEnum):
    """Persisted digest generation status."""

    GENERATED = "generated"
    FAILED = "failed"


class DeliveryStatus(StrEnum):
    """Persisted digest delivery status."""

    SUCCEEDED = "succeeded"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class NewTopic:
    """Topic ready for persistence."""

    slug: str
    name: str
    description: str
    query: str
    rules: dict[str, object]
    preferred_categories: tuple[str, ...]
    enabled: bool = True


@dataclass(frozen=True, slots=True)
class StoredTopic(NewTopic):
    """Persisted topic."""

    id: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class NewSubscription:
    """Subscription ready for persistence."""

    name: str
    discovery_query: str
    topic_ids: tuple[int, ...]
    minimum_relevance_score: float
    preferred_categories: tuple[str, ...]
    digest_cadence: DigestCadence
    delivery_destination: str | None = None
    enabled: bool = True
    last_processed_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class StoredSubscription(NewSubscription):
    """Persisted subscription."""

    id: int = 0
    topics: tuple[StoredTopic, ...] = ()
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class DiscoverySearchRequest:
    """Provider-independent discovery search request."""

    topic_query: str
    from_publication_date: date
    until_publication_date: date
    rows: int
    offset: int = 0


@dataclass(frozen=True, slots=True)
class DiscoveryCandidate:
    """Provider-independent candidate paper metadata."""

    title: str
    doi: str | None
    abstract: str | None
    journal: str | None
    publication_date: date | None
    source_url: str | None
    authors: tuple[str, ...]
    provider_name: str
    provider_record_id: str | None
    raw_score: float | None = None


@dataclass(frozen=True, slots=True)
class DiscoverySearchResult:
    """Provider-independent discovery search result."""

    candidates: tuple[DiscoveryCandidate, ...]
    provider_name: str
    query: str
    rows: int
    offset: int


@dataclass(frozen=True, slots=True)
class StoredDiscoveryRun:
    """Persisted discovery run summary."""

    id: int
    subscription_id: int
    topic_id: int | None
    provider: str
    query: str
    from_publication_date: date
    until_publication_date: date
    status: DiscoveryRunStatus
    error: str | None
    started_at: datetime
    completed_at: datetime | None


@dataclass(frozen=True, slots=True)
class StoredDiscoveryCandidate:
    """Persisted candidate outcome."""

    id: int
    discovery_run_id: int
    provider: str
    provider_record_id: str | None
    doi: str | None
    normalized_doi: str | None
    title: str
    normalized_title: str
    publication_date: date | None
    status: DiscoveryCandidateStatus
    paper_id: int | None
    relevance_score: float | None
    rank_position: int | None
    outcome_reason: str | None


@dataclass(frozen=True, slots=True)
class DigestPaper:
    """One paper selected for a digest."""

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


@dataclass(frozen=True, slots=True)
class StoredDigest:
    """Persisted digest."""

    id: int
    idempotency_key: str
    subscription_id: int
    topic_id: int | None
    digest_date: date
    period_start: date
    period_end: date
    status: DigestStatus
    title: str
    plain_text: str
    html: str
    selected_papers: tuple[DigestPaper, ...]
    error: str | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class StoredDigestDelivery:
    """Persisted delivery attempt."""

    id: int
    digest_id: int
    provider: str
    destination: str | None
    status: DeliveryStatus
    idempotency_key: str
    error: str | None
    created_at: datetime
    completed_at: datetime | None


@dataclass(frozen=True, slots=True)
class DigestRunResult:
    """Result returned by manual digest workflows."""

    subscription: StoredSubscription
    discovery_runs: tuple[StoredDiscoveryRun, ...]
    candidates: tuple[StoredDiscoveryCandidate, ...]
    digest: StoredDigest
    delivery: StoredDigestDelivery
