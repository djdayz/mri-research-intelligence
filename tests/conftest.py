from collections.abc import Iterator

import pytest
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from mrinsight.core.config import get_settings
from mrinsight.db.session import create_database_engine


@pytest.fixture(scope="session")
def test_engine() -> Iterator[Engine]:
    """Create one engine connected to the test database."""

    settings = get_settings()

    if settings.test_database_url is None:
        raise RuntimeError(
            "MRINSIGHT_TEST_DATABASE_URL is required for database tests."
        )

    engine = create_database_engine(settings.test_database_url)

    yield engine

    engine.dispose()


@pytest.fixture
def db_session(
    test_engine: Engine,
) -> Iterator[Session]:
    """Provide a transaction-isolated database session."""

    with test_engine.connect() as connection:
        outer_transaction = connection.begin()

        session = Session(
            bind=connection,
            join_transaction_mode="create_savepoint",
        )

        try:
            yield session
        finally:
            session.close()

            if outer_transaction.is_active:
                outer_transaction.rollback()
