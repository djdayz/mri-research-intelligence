from datetime import date
from typing import Protocol

from mrinsight.discovery.records import (
    DeliveryStatus,
    DigestPaper,
    DigestStatus,
    DiscoveryCandidate,
    DiscoveryCandidateStatus,
    DiscoveryRunStatus,
    NewSubscription,
    StoredDigest,
    StoredDigestDelivery,
    StoredDiscoveryCandidate,
    StoredDiscoveryRun,
    StoredSubscription,
    StoredTopic,
)
from mrinsight.papers import NewPaper, StoredPaper


class DiscoveryRepository(Protocol):
    """Persistence contract for discovery and digest workflows."""

    def list_topics(self) -> tuple[StoredTopic, ...]:
        """Return enabled topics."""

    def add_subscription(
        self,
        subscription: NewSubscription,
    ) -> StoredSubscription:
        """Persist a subscription."""

    def list_subscriptions(self) -> tuple[StoredSubscription, ...]:
        """Return subscriptions ordered newest first."""

    def get_subscription(
        self,
        subscription_id: int,
    ) -> StoredSubscription | None:
        """Return one subscription."""

    def add_discovery_run(
        self,
        *,
        subscription_id: int,
        topic_id: int | None,
        provider: str,
        query: str,
        from_publication_date: date,
        until_publication_date: date,
    ) -> StoredDiscoveryRun:
        """Persist a running discovery run."""

    def complete_discovery_run(
        self,
        run_id: int,
        *,
        status: DiscoveryRunStatus,
        error: str | None,
    ) -> StoredDiscoveryRun:
        """Mark a discovery run complete."""

    def add_discovery_candidate(
        self,
        *,
        run_id: int,
        candidate: DiscoveryCandidate,
        normalized_doi: str | None,
        normalized_title: str,
        status: DiscoveryCandidateStatus,
        paper_id: int | None,
        relevance_score: float | None,
        rank_position: int | None,
        outcome_reason: str | None,
    ) -> StoredDiscoveryCandidate:
        """Persist one candidate outcome."""

    def find_paper_by_doi(
        self,
        normalized_doi: str,
    ) -> StoredPaper | None:
        """Return existing paper by canonical DOI."""

    def find_paper_by_title_year(
        self,
        *,
        normalized_title: str,
        publication_year: int,
    ) -> StoredPaper | None:
        """Return conservative title-year duplicate candidate."""

    def add_paper(
        self,
        paper: NewPaper,
    ) -> StoredPaper:
        """Persist a paper discovered without singleton DOI lookup."""

    def add_digest(
        self,
        *,
        subscription_id: int,
        topic_id: int | None,
        digest_date: date,
        period_start: date,
        period_end: date,
        status: DigestStatus,
        title: str,
        plain_text: str,
        html: str,
        selected_papers: tuple[DigestPaper, ...],
        error: str | None,
    ) -> StoredDigest:
        """Persist one digest."""

    def add_delivery(
        self,
        *,
        digest_id: int,
        provider: str,
        destination: str | None,
        status: DeliveryStatus,
        idempotency_key: str,
        error: str | None,
    ) -> StoredDigestDelivery:
        """Persist one delivery attempt."""

    def get_digest(
        self,
        digest_id: int,
    ) -> StoredDigest | None:
        """Return one digest."""
