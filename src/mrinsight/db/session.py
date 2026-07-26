from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker


def create_database_engine(database_url: str) -> Engine:
    """Create the application's SQLAlchemy database engine"""

    return create_engine(
        database_url,
        pool_pre_ping=True,
    )


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Create a factory producing database sessions"""

    return sessionmaker(
        bind=engine,
        class_=Session,
    )
