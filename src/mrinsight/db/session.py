from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker


def create_database_engine(database_url: str) -> Engine:
    """Create the SQLAlchemy engine used by the application."""

    return create_engine(
        database_url,
        pool_pre_ping=True,
    )


def create_pooled_database_engine(
    database_url: str,
    *,
    pool_size: int,
    max_overflow: int,
    pool_timeout_seconds: float,
    pool_recycle_seconds: int,
) -> Engine:
    """Create a configured SQLAlchemy engine for long-running processes."""

    return create_engine(
        database_url,
        pool_pre_ping=True,
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_timeout=pool_timeout_seconds,
        pool_recycle=pool_recycle_seconds,
    )


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Create a configured SQLAlchemy session factory."""

    return sessionmaker(
        bind=engine,
        class_=Session,
        autoflush=False,
        expire_on_commit=False,
    )
