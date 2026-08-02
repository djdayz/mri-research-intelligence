from __future__ import annotations

import argparse
from collections.abc import Sequence

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
from mrinsight.db.repositories import (
    SqlAlchemyDiscoveryRepository,
    SqlAlchemyPaperChunkRepository,
    SqlAlchemyPaperContentRepository,
    SqlAlchemyPaperRepository,
    SqlAlchemyRelevanceAssessmentRepository,
)


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

    args = parser.parse_args(argv)

    if args.command == "digest" and args.digest_command == "run":
        return _run_digest_preview(
            subscription_id=args.subscription_id,
            rows=args.rows,
        )

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
