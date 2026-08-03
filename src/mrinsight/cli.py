from __future__ import annotations

import argparse
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from mrinsight.api.dependencies import (
    get_database_session_factory,
    get_digest_delivery_provider,
    get_discovery_provider,
    get_rule_based_relevance_scorer,
)
from mrinsight.application.services import (
    AssessPaperRelevanceService,
    BuildPaperChunksService,
    RunDigestPreviewService,
    SelectAnalysisContentService,
    StoreAbstractContentService,
)
from mrinsight.core.config import get_settings
from mrinsight.db.models import Subscription
from mrinsight.db.repositories import (
    SqlAlchemyDiscoveryRepository,
    SqlAlchemyPaperChunkRepository,
    SqlAlchemyPaperContentRepository,
    SqlAlchemyPaperRepository,
    SqlAlchemyRelevanceAssessmentRepository,
)
from mrinsight.discovery import DigestCadence, NewSubscription, StoredSubscription

DEMO_SUBSCRIPTION_NAME = "Demo MRI CVR weekly digest"


def main(
    argv: Sequence[str] | None = None,
) -> int:
    """Run the MRInsight CLI."""

    parser = argparse.ArgumentParser(prog="mrinsight")
    subparsers = parser.add_subparsers(dest="command", required=True)
    digest_parser = subparsers.add_parser("digest")
    digest_subparsers = digest_parser.add_subparsers(
        dest="digest_command",
        required=True,
    )
    run_parser = digest_subparsers.add_parser("run")
    run_parser.add_argument("--subscription-id", type=int, required=True)
    run_parser.add_argument("--rows", type=int, default=20)
    run_due_parser = digest_subparsers.add_parser("run-due")
    run_due_parser.add_argument("--rows", type=int, default=20)
    retry_parser = digest_subparsers.add_parser("retry-deliveries")
    retry_parser.add_argument("--limit", type=int, default=20)
    seed_parser = subparsers.add_parser("seed")
    seed_subparsers = seed_parser.add_subparsers(
        dest="seed_command",
        required=True,
    )
    seed_subparsers.add_parser("demo")

    args = parser.parse_args(argv)

    if args.command == "digest" and args.digest_command == "run":
        return _run_digest_preview(
            subscription_id=args.subscription_id,
            rows=args.rows,
        )
    if args.command == "digest" and args.digest_command == "run-due":
        return _run_due_digest_previews(rows=args.rows)
    if args.command == "digest" and args.digest_command == "retry-deliveries":
        return _retry_due_deliveries(limit=args.limit)
    if args.command == "seed" and args.seed_command == "demo":
        return _seed_demo()

    parser.error("Unsupported command.")
    return 2


def _run_digest_preview(
    *,
    subscription_id: int,
    rows: int,
) -> int:
    """Run digest preview using configured local dependencies."""

    session_factory = get_database_session_factory()
    with session_factory() as session:
        service = _build_digest_service(session)
        result = service.execute(subscription_id=subscription_id, rows=rows)
        session.commit()

    print(
        f"Created digest {result.digest.id} with "
        f"{len(result.digest.selected_papers)} papers."
    )
    return 0


def _run_due_digest_previews(
    *,
    rows: int,
) -> int:
    """Run due subscriptions once for cron or container schedulers."""

    now = datetime.now(UTC)
    session_factory = get_database_session_factory()
    with session_factory() as session:
        repository = SqlAlchemyDiscoveryRepository(session)
        subscriptions = tuple(
            subscription
            for subscription in repository.list_subscriptions()
            if _is_subscription_due(subscription, now)
        )

    processed_count = 0
    for subscription in subscriptions:
        with session_factory() as session:
            repository = SqlAlchemyDiscoveryRepository(session)
            service = _build_digest_service(session)
            result = service.execute(subscription_id=subscription.id, rows=rows)
            repository.mark_subscription_processed_at(
                subscription.id,
                processed_at=now,
            )
            session.commit()
        processed_count += 1
        print(f"Created digest {result.digest.id} for subscription {subscription.id}.")

    print(f"Processed {processed_count} due subscriptions.")
    return 0


def _retry_due_deliveries(
    *,
    limit: int,
) -> int:
    """Retry due failed delivery attempts once and exit."""

    now = datetime.now(UTC)
    provider = get_digest_delivery_provider()
    session_factory = get_database_session_factory()
    with session_factory() as session:
        repository = SqlAlchemyDiscoveryRepository(session)
        due_deliveries = repository.list_retryable_deliveries_due(
            provider=provider.name,
            due_at=now,
            limit=limit,
        )

    retried_count = 0
    for delivery in due_deliveries:
        with session_factory() as session:
            repository = SqlAlchemyDiscoveryRepository(session)
            digest = repository.get_digest(delivery.digest_id)
            if digest is None:
                repository.mark_delivery_retry_consumed(delivery.id)
                session.commit()
                continue
            service = _build_digest_service(session)
            retry = service._deliver_digest(
                digest,
                destination=delivery.destination,
                idempotency_key=(
                    f"{delivery.idempotency_key}:retry:{delivery.attempt_count + 1}"
                ),
                attempt_count=delivery.attempt_count + 1,
            )
            repository.mark_delivery_retry_consumed(delivery.id)
            session.commit()
        retried_count += 1
        print(
            f"Retried delivery {delivery.id}; "
            f"new delivery {retry.id} status {retry.status.value}."
        )

    print(f"Retried {retried_count} due deliveries.")
    return 0


def _seed_demo() -> int:
    """Create repeatable local demo records."""

    session_factory = get_database_session_factory()
    with session_factory() as session:
        repository = SqlAlchemyDiscoveryRepository(session)
        existing_subscription = _find_subscription_by_name(
            session,
            DEMO_SUBSCRIPTION_NAME,
        )
        if existing_subscription is not None:
            session.commit()
            print(
                f"Demo subscription already exists with id {existing_subscription.id}."
            )
            return 0

        topics = repository.list_topics()
        if not topics:
            raise RuntimeError("No enabled topics exist. Run Alembic migrations first.")

        preferred_topic = next(
            (topic for topic in topics if topic.slug == "mri-cvr-mapping"),
            topics[0],
        )
        subscription = repository.add_subscription(
            NewSubscription(
                name=DEMO_SUBSCRIPTION_NAME,
                discovery_query="MRI cerebrovascular reactivity BOLD",
                topic_ids=(preferred_topic.id,),
                minimum_relevance_score=0.0,
                preferred_categories=("mri", "cvr"),
                digest_cadence=DigestCadence.WEEKLY,
                delivery_destination="var/digests",
            )
        )
        session.commit()

    print(f"Created demo subscription {subscription.id}.")
    return 0


def _find_subscription_by_name(
    session: Session,
    name: str,
) -> Subscription | None:
    """Return a subscription model by exact demo name."""

    return session.execute(
        select(Subscription).where(Subscription.name == name)
    ).scalar_one_or_none()


def _is_subscription_due(
    subscription: StoredSubscription,
    now: datetime,
) -> bool:
    """Return whether a subscription should run in a scheduled invocation."""

    if not subscription.enabled:
        return False
    if subscription.digest_cadence is DigestCadence.MANUAL:
        return False
    if subscription.last_processed_at is None:
        return True

    cadence_intervals = {
        DigestCadence.DAILY: timedelta(days=1),
        DigestCadence.WEEKLY: timedelta(days=7),
        DigestCadence.MONTHLY: timedelta(days=30),
    }
    interval = cadence_intervals[subscription.digest_cadence]
    return subscription.last_processed_at <= now - interval


def _build_digest_service(
    session: Session,
) -> RunDigestPreviewService:
    """Construct digest workflow service for CLI."""

    discovery_repository = SqlAlchemyDiscoveryRepository(session)
    paper_repository = SqlAlchemyPaperRepository(session)
    content_repository = SqlAlchemyPaperContentRepository(session)
    chunk_repository = SqlAlchemyPaperChunkRepository(session)
    relevance_repository = SqlAlchemyRelevanceAssessmentRepository(session)
    content_selector = SelectAnalysisContentService(content_repository)

    return RunDigestPreviewService(
        discovery_repository=discovery_repository,
        abstract_content_service=StoreAbstractContentService(content_repository),
        chunk_service=BuildPaperChunksService(chunk_repository),
        relevance_service=AssessPaperRelevanceService(
            paper_repository=paper_repository,
            content_selector=content_selector,
            chunk_repository=chunk_repository,
            assessment_repository=relevance_repository,
            scorer=get_rule_based_relevance_scorer(),
        ),
        discovery_provider=get_discovery_provider(),
        delivery_provider=get_digest_delivery_provider(),
        delivery_retry_delay_seconds=get_settings().digest_delivery_retry_delay_seconds,
    )


if __name__ == "__main__":
    raise SystemExit(main())
