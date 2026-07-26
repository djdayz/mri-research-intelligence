from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker


def check_database_connection(
    session_factory: sessionmaker[Session],
) -> None:
    """Raise an exception when PostgreSQL cannot execute a trivial query"""

    with session_factory() as session:
        result = session.execute(text("SELECT 1")).scalar_one()

    if result != 1:
        raise RuntimeError("Unexpected database health check result.")
