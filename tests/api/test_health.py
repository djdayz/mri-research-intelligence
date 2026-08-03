import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from mrinsight.api.dependencies import get_database_session_factory
from mrinsight.main import app


def test_health_check_returns_service_status() -> None:
    # Use TestClient to simulate requests to the FastAPI app.
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "mrinsight",
    }


def test_request_id_header_is_returned() -> None:
    with TestClient(app) as client:
        response = client.get("/health", headers={"x-request-id": "test-request-1"})

    assert response.status_code == 200
    assert response.headers["x-request-id"] == "test-request-1"


@pytest.mark.integration
def test_readiness_check_returns_database_status(
    db_session: Session,
) -> None:
    connection = db_session.connection()
    factory = sessionmaker(
        bind=connection,
        class_=Session,
        join_transaction_mode="create_savepoint",
    )

    def override_session_factory() -> sessionmaker[Session]:
        return factory

    app.dependency_overrides[get_database_session_factory] = override_session_factory
    try:
        with TestClient(app) as client:
            response = client.get("/ready")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "service": "mrinsight",
        "database": "ok",
    }
