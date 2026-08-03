from __future__ import annotations

import argparse
from collections.abc import Sequence

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
from mrinsight.db.models import Subscription
from mrinsight.db.repositories import (
    SqlAlchemyDiscoveryRepository,
    SqlAlchemyPaperChunkRepository,
    SqlAlchemyPaperContentRepository,
    SqlAlchemyPaperRepository,
    SqlAlchemyRelevanceAssessmentRepository,
)
from mrinsight.discovery import DigestCadence, NewSubscription

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
    )


if __name__ == "__main__":
    raise SystemExit(main())
