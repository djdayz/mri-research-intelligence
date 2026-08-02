from datetime import UTC, date, datetime
from typing import cast

from sqlalchemy import extract, select
from sqlalchemy.orm import Session

from mrinsight.db.models import (
    Digest,
    DigestDelivery,
    DiscoveryCandidateModel,
    DiscoveryRun,
    Paper,
    Subscription,
    SubscriptionTopic,
    Topic,
)
from mrinsight.discovery.records import (
    DeliveryStatus,
    DigestCadence,
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


class SqlAlchemyDiscoveryRepository:
    """Persist discovery, subscription, and digest records."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_topics(self) -> tuple[StoredTopic, ...]:
        """Return enabled topics."""

        models = self._session.execute(
            select(Topic).where(Topic.enabled.is_(True)).order_by(Topic.name.asc())
        ).scalars()

        return tuple(_to_topic(model) for model in models)

    def add_subscription(
        self,
        subscription: NewSubscription,
    ) -> StoredSubscription:
        """Persist a subscription."""

        model = Subscription(
            name=subscription.name,
            discovery_query=subscription.discovery_query,
            minimum_relevance_score=subscription.minimum_relevance_score,
            preferred_categories=list(subscription.preferred_categories),
            digest_cadence=subscription.digest_cadence.value,
            delivery_destination=subscription.delivery_destination,
            enabled=subscription.enabled,
            last_processed_at=subscription.last_processed_at,
        )
        self._session.add(model)
        self._session.flush()
        self._session.add_all(
            SubscriptionTopic(subscription_id=model.id, topic_id=topic_id)
            for topic_id in subscription.topic_ids
        )
        self._session.flush()
        self._session.refresh(model)

        stored = self.get_subscription(model.id)
        if stored is None:
            raise RuntimeError("Stored subscription disappeared after insert.")
        return stored

    def list_subscriptions(self) -> tuple[StoredSubscription, ...]:
        """Return subscriptions ordered newest first."""

        models = self._session.execute(
            select(Subscription).order_by(
                Subscription.created_at.desc(),
                Subscription.id.desc(),
            )
        ).scalars()

        return tuple(self._to_subscription(model) for model in models)

    def get_subscription(
        self,
        subscription_id: int,
    ) -> StoredSubscription | None:
        """Return one subscription."""

        model = self._session.get(Subscription, subscription_id)
        if model is None:
            return None
        return self._to_subscription(model)

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

        model = DiscoveryRun(
            subscription_id=subscription_id,
            topic_id=topic_id,
            provider=provider,
            query=query,
            from_publication_date=from_publication_date,
            until_publication_date=until_publication_date,
            status=DiscoveryRunStatus.RUNNING.value,
        )
        self._session.add(model)
        self._session.flush()
        self._session.refresh(model)

        return _to_discovery_run(model)

    def complete_discovery_run(
        self,
        run_id: int,
        *,
        status: DiscoveryRunStatus,
        error: str | None,
    ) -> StoredDiscoveryRun:
        """Mark a discovery run complete."""

        model = self._session.get(DiscoveryRun, run_id)
        if model is None:
            raise RuntimeError(f"Discovery run {run_id} does not exist.")

        model.status = status.value
        model.error = error
        model.completed_at = datetime.now(UTC)
        self._session.flush()
        self._session.refresh(model)

        return _to_discovery_run(model)

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

        model = DiscoveryCandidateModel(
            discovery_run_id=run_id,
            provider=candidate.provider_name,
            provider_record_id=candidate.provider_record_id,
            doi=candidate.doi,
            normalized_doi=normalized_doi,
            title=candidate.title,
            normalized_title=normalized_title,
            publication_date=candidate.publication_date,
            status=status.value,
            paper_id=paper_id,
            relevance_score=relevance_score,
            rank_position=rank_position,
            outcome_reason=outcome_reason,
        )
        self._session.add(model)
        self._session.flush()
        self._session.refresh(model)

        return _to_discovery_candidate(model)

    def find_paper_by_doi(
        self,
        normalized_doi: str,
    ) -> StoredPaper | None:
        """Return existing paper by canonical DOI."""

        model = self._session.execute(
            select(Paper).where(Paper.normalized_doi == normalized_doi)
        ).scalar_one_or_none()

        return _to_paper(model) if model is not None else None

    def find_paper_by_title_year(
        self,
        *,
        normalized_title: str,
        publication_year: int,
    ) -> StoredPaper | None:
        """Return conservative title-year duplicate candidate."""

        model = self._session.execute(
            select(Paper).where(
                Paper.normalized_title == normalized_title,
                extract("year", Paper.publication_date) == publication_year,
            )
        ).scalar_one_or_none()

        return _to_paper(model) if model is not None else None

    def add_paper(
        self,
        paper: NewPaper,
    ) -> StoredPaper:
        """Persist a paper discovered without singleton DOI lookup."""

        model = Paper(
            doi=paper.doi,
            normalized_doi=paper.normalized_doi,
            title=paper.title,
            normalized_title=paper.normalized_title,
            abstract=paper.abstract,
            journal=paper.journal,
            publication_date=paper.publication_date,
            source_url=paper.source_url,
            ingestion_source=paper.ingestion_source,
            provider_record_id=paper.provider_record_id,
        )
        self._session.add(model)
        self._session.flush()
        self._session.refresh(model)

        return _to_paper(model)

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

        model = Digest(
            subscription_id=subscription_id,
            topic_id=topic_id,
            digest_date=digest_date,
            period_start=period_start,
            period_end=period_end,
            status=status.value,
            title=title,
            plain_text=plain_text,
            html=html,
            selected_papers=[_digest_paper_to_json(paper) for paper in selected_papers],
            error=error,
        )
        self._session.add(model)
        self._session.flush()
        self._session.refresh(model)

        return _to_digest(model)

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

        model = DigestDelivery(
            digest_id=digest_id,
            provider=provider,
            destination=destination,
            status=status.value,
            idempotency_key=idempotency_key,
            error=error,
            completed_at=datetime.now(UTC),
        )
        self._session.add(model)
        self._session.flush()
        self._session.refresh(model)

        return _to_digest_delivery(model)

    def get_digest(
        self,
        digest_id: int,
    ) -> StoredDigest | None:
        """Return one digest."""

        model = self._session.get(Digest, digest_id)
        return _to_digest(model) if model is not None else None

    def _to_subscription(
        self,
        model: Subscription,
    ) -> StoredSubscription:
        """Translate subscription model."""

        topic_ids = tuple(
            row[0]
            for row in self._session.execute(
                select(SubscriptionTopic.topic_id)
                .where(SubscriptionTopic.subscription_id == model.id)
                .order_by(SubscriptionTopic.topic_id.asc())
            ).all()
        )
        topics = tuple(
            _to_topic(topic)
            for topic in self._session.execute(
                select(Topic).where(Topic.id.in_(topic_ids)).order_by(Topic.name.asc())
            ).scalars()
        )

        return StoredSubscription(
            id=model.id,
            name=model.name,
            discovery_query=model.discovery_query,
            topic_ids=topic_ids,
            topics=topics,
            minimum_relevance_score=model.minimum_relevance_score,
            preferred_categories=tuple(model.preferred_categories),
            digest_cadence=DigestCadence(model.digest_cadence),
            delivery_destination=model.delivery_destination,
            enabled=model.enabled,
            last_processed_at=model.last_processed_at,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )


def _to_topic(
    model: Topic,
) -> StoredTopic:
    """Translate topic model."""

    return StoredTopic(
        id=model.id,
        slug=model.slug,
        name=model.name,
        description=model.description,
        query=model.query,
        rules=model.rules,
        preferred_categories=tuple(model.preferred_categories),
        enabled=model.enabled,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _to_discovery_run(
    model: DiscoveryRun,
) -> StoredDiscoveryRun:
    """Translate discovery run model."""

    return StoredDiscoveryRun(
        id=model.id,
        subscription_id=model.subscription_id,
        topic_id=model.topic_id,
        provider=model.provider,
        query=model.query,
        from_publication_date=model.from_publication_date,
        until_publication_date=model.until_publication_date,
        status=DiscoveryRunStatus(model.status),
        error=model.error,
        started_at=model.started_at,
        completed_at=model.completed_at,
    )


def _to_discovery_candidate(
    model: DiscoveryCandidateModel,
) -> StoredDiscoveryCandidate:
    """Translate discovery candidate model."""

    return StoredDiscoveryCandidate(
        id=model.id,
        discovery_run_id=model.discovery_run_id,
        provider=model.provider,
        provider_record_id=model.provider_record_id,
        doi=model.doi,
        normalized_doi=model.normalized_doi,
        title=model.title,
        normalized_title=model.normalized_title,
        publication_date=model.publication_date,
        status=DiscoveryCandidateStatus(model.status),
        paper_id=model.paper_id,
        relevance_score=model.relevance_score,
        rank_position=model.rank_position,
        outcome_reason=model.outcome_reason,
    )


def _to_digest(
    model: Digest,
) -> StoredDigest:
    """Translate digest model."""

    return StoredDigest(
        id=model.id,
        subscription_id=model.subscription_id,
        topic_id=model.topic_id,
        digest_date=model.digest_date,
        period_start=model.period_start,
        period_end=model.period_end,
        status=DigestStatus(model.status),
        title=model.title,
        plain_text=model.plain_text,
        html=model.html,
        selected_papers=tuple(
            _digest_paper_from_json(item) for item in model.selected_papers
        ),
        error=model.error,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _to_digest_delivery(
    model: DigestDelivery,
) -> StoredDigestDelivery:
    """Translate digest delivery model."""

    return StoredDigestDelivery(
        id=model.id,
        digest_id=model.digest_id,
        provider=model.provider,
        destination=model.destination,
        status=DeliveryStatus(model.status),
        idempotency_key=model.idempotency_key,
        error=model.error,
        created_at=model.created_at,
        completed_at=model.completed_at,
    )


def _to_paper(
    model: Paper,
) -> StoredPaper:
    """Translate paper model."""

    return StoredPaper(
        id=model.id,
        doi=model.doi,
        normalized_doi=model.normalized_doi,
        title=model.title,
        normalized_title=model.normalized_title,
        abstract=model.abstract,
        journal=model.journal,
        publication_date=model.publication_date,
        source_url=model.source_url,
        ingestion_source=model.ingestion_source,
        provider_record_id=model.provider_record_id,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _digest_paper_to_json(
    paper: DigestPaper,
) -> dict[str, object]:
    """Return JSON-safe digest paper payload."""

    return {
        "paper_id": paper.paper_id,
        "doi": paper.doi,
        "title": paper.title,
        "journal": paper.journal,
        "publication_date": (
            paper.publication_date.isoformat()
            if paper.publication_date is not None
            else None
        ),
        "relevance_score": paper.relevance_score,
        "analysis_scope": paper.analysis_scope,
        "concise_summary": paper.concise_summary,
        "methodology_highlights": list(paper.methodology_highlights),
        "main_results": list(paper.main_results),
        "limitations": list(paper.limitations),
        "link": paper.link,
        "provenance": paper.provenance,
        "ranking_explanation": paper.ranking_explanation,
    }


def _digest_paper_from_json(
    payload: dict[str, object],
) -> DigestPaper:
    """Return typed digest paper from JSON payload."""

    publication_date_value = payload.get("publication_date")
    publication_date = (
        date.fromisoformat(publication_date_value)
        if isinstance(publication_date_value, str)
        else None
    )

    return DigestPaper(
        paper_id=cast(int, payload["paper_id"]),
        doi=cast(str | None, payload.get("doi")),
        title=cast(str, payload["title"]),
        journal=cast(str | None, payload.get("journal")),
        publication_date=publication_date,
        relevance_score=cast(float | None, payload.get("relevance_score")),
        analysis_scope=cast(str | None, payload.get("analysis_scope")),
        concise_summary=cast(str, payload["concise_summary"]),
        methodology_highlights=tuple(
            cast(list[str], payload.get("methodology_highlights", []))
        ),
        main_results=tuple(cast(list[str], payload.get("main_results", []))),
        limitations=tuple(cast(list[str], payload.get("limitations", []))),
        link=cast(str | None, payload.get("link")),
        provenance=cast(str, payload["provenance"]),
        ranking_explanation=cast(str, payload["ranking_explanation"]),
    )
