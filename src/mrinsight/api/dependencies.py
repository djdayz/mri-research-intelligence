from collections.abc import Iterator
from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from mrinsight.application.services import IngestPaperService
from mrinsight.core.config import get_settings
from mrinsight.db.repositories import (
    SqlAlchemyPaperRepository,
)
from mrinsight.db.session import (
    create_database_engine,
    create_session_factory,
)
from mrinsight.papers.providers import (
    BibliographicProvider,
    UnconfiguredBibliographicProvider,
)
from mrinsight.papers.repositories import PaperRepository


@lru_cache
def get_database_engine() -> Engine:
    """Return the process-wide SQLAlchemy engine."""

    settings = get_settings()

    return create_database_engine(settings.database_url)


@lru_cache
def get_database_session_factory() -> sessionmaker[Session]:
    """Return the process-wide database session factory."""

    return create_session_factory(get_database_engine())


def get_db_session() -> Iterator[Session]:
    """Provide one transaction-scoped database session."""

    session_factory = get_database_session_factory()

    with session_factory() as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise


@lru_cache
def get_bibliographic_provider() -> BibliographicProvider:
    """Return the configured bibliographic provider."""

    return UnconfiguredBibliographicProvider()


def get_paper_repository(
    session: Annotated[
        Session,
        Depends(get_db_session),
    ],
) -> PaperRepository:
    """Construct the SQLAlchemy paper repository."""

    return SqlAlchemyPaperRepository(session)


def get_ingest_paper_service(
    provider: Annotated[
        BibliographicProvider,
        Depends(get_bibliographic_provider),
    ],
    repository: Annotated[
        PaperRepository,
        Depends(get_paper_repository),
    ],
) -> IngestPaperService:
    """Construct the DOI-ingestion application service."""

    return IngestPaperService(
        provider=provider,
        repository=repository,
    )
