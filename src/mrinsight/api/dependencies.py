from collections.abc import Iterator
from functools import lru_cache
from typing import Annotated

import httpx
from fastapi import Depends
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from mrinsight.application.services import (
    BuildPaperChunksService,
    IngestPaperService,
    StoreAbstractContentService,
)
from mrinsight.core.config import get_settings
from mrinsight.db.repositories import (
    SqlAlchemyPaperChunkRepository,
    SqlAlchemyPaperContentRepository,
    SqlAlchemyPaperRepository,
)
from mrinsight.db.session import (
    create_database_engine,
    create_session_factory,
)
from mrinsight.papers.providers import (
    BibliographicProvider,
    CrossrefBibliographicProvider,
    UnconfiguredBibliographicProvider,
)
from mrinsight.papers.repositories import (
    PaperChunkRepository,
    PaperContentRepository,
    PaperRepository,
)


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

    settings = get_settings()

    if not settings.crossref_mailto:
        return UnconfiguredBibliographicProvider()

    return CrossrefBibliographicProvider(
        client=get_http_client(),
        mailto=settings.crossref_mailto,
        user_agent=settings.crossref_user_agent,
        base_url=settings.crossref_base_url,
        max_attempts=settings.crossref_max_attempts,
        backoff_seconds=(settings.crossref_backoff_seconds),
    )


def get_paper_repository(
    session: Annotated[
        Session,
        Depends(get_db_session),
    ],
) -> PaperRepository:
    """Construct the SQLAlchemy paper repository."""

    return SqlAlchemyPaperRepository(session)


def get_paper_content_repository(
    session: Annotated[
        Session,
        Depends(get_db_session),
    ],
) -> PaperContentRepository:
    """Construct the SQLAlchemy paper-content repository."""

    return SqlAlchemyPaperContentRepository(session)


def get_store_abstract_content_service(
    repository: Annotated[
        PaperContentRepository,
        Depends(get_paper_content_repository),
    ],
) -> StoreAbstractContentService:
    """Construct the abstract-content storage service."""

    return StoreAbstractContentService(repository)


def get_paper_chunk_repository(
    session: Annotated[
        Session,
        Depends(get_db_session),
    ],
) -> PaperChunkRepository:
    """Construct the SQLAlchemy chunk repository."""

    return SqlAlchemyPaperChunkRepository(session)


def get_build_paper_chunks_service(
    repository: Annotated[
        PaperChunkRepository,
        Depends(get_paper_chunk_repository),
    ],
) -> BuildPaperChunksService:
    """Construct the chunk-building service."""

    return BuildPaperChunksService(repository)


def get_ingest_paper_service(
    provider: Annotated[
        BibliographicProvider,
        Depends(get_bibliographic_provider),
    ],
    repository: Annotated[
        PaperRepository,
        Depends(get_paper_repository),
    ],
    abstract_content_service: Annotated[
        StoreAbstractContentService,
        Depends(get_store_abstract_content_service),
    ],
    chunk_service: Annotated[
        BuildPaperChunksService,
        Depends(get_build_paper_chunks_service),
    ],
) -> IngestPaperService:
    """Construct the DOI-ingestion application service."""

    return IngestPaperService(
        provider=provider,
        repository=repository,
        abstract_content_service=(abstract_content_service),
        chunk_service=chunk_service,
    )


@lru_cache
def get_http_client() -> httpx.Client:
    """Return the process-wide outbound HTTP client."""

    settings = get_settings()

    timeout = httpx.Timeout(
        settings.crossref_timeout_seconds,
        connect=(settings.crossref_connect_timeout_seconds),
    )

    return httpx.Client(
        timeout=timeout,
        follow_redirects=True,
    )


def close_application_resources() -> None:
    """Close process-wide database and HTTP resources."""

    get_bibliographic_provider.cache_clear()

    if get_http_client.cache_info().currsize:
        get_http_client().close()
        get_http_client.cache_clear()

    get_database_session_factory.cache_clear()

    if get_database_engine.cache_info().currsize:
        get_database_engine().dispose()
        get_database_engine.cache_clear()
