from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker


def check_database_connection(session_factory: sessionmaker[Session]) -> None:
    """Run a lightweight query to verify database connectivity."""

    with session_factory() as session:
        session.execute(text("SELECT 1"))
