import pytest
from sqlalchemy import Engine

from mrinsight.db.health import check_database_connection
from mrinsight.db.session import create_session_factory


@pytest.mark.integration
def test_configured_postgresql_database_is_reachable(
    test_engine: Engine,
) -> None:
    session_factory = create_session_factory(test_engine)

    check_database_connection(session_factory)
