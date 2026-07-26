import pytest

from mrinsight.core.config import get_settings
from mrinsight.db.health import check_database_connection
from mrinsight.db.session import create_database_engine, create_session_factory


@pytest.mark.integration
def test_configured_postgresql_database_is_reachable() -> None:
    settings = get_settings()
    engine = create_database_engine(settings.database_url)
    session_factory = create_session_factory(engine)

    try:
        check_database_connection(session_factory)
    finally:
        engine.dispose()
