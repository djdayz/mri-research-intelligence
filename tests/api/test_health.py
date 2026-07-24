from fastapi.testclient import TestClient

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
