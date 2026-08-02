from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from tests.integration.db.test_retrieval_repository import create_search_fixture

from mrinsight.api.dependencies import get_db_session
from mrinsight.main import app


@pytest.fixture
def retrieval_client(
    db_session: Session,
) -> Iterator[TestClient]:
    """Create an API client sharing the transaction-isolated test session."""

    def override_db_session() -> Iterator[Session]:
        try:
            yield db_session
            db_session.commit()
        except Exception:
            db_session.rollback()
            raise

    app.dependency_overrides[get_db_session] = override_db_session

    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()


@pytest.mark.integration
def test_list_papers_empty_state(
    retrieval_client: TestClient,
) -> None:
    response = retrieval_client.get("/papers")

    assert response.status_code == 200
    assert response.json() == {
        "items": [],
        "total": 0,
        "limit": 25,
        "offset": 0,
        "sort": "newest_ingestion",
        "next_offset": None,
    }


@pytest.mark.integration
def test_list_papers_supports_pagination_sorting_and_filters(
    retrieval_client: TestClient,
    db_session: Session,
) -> None:
    first, _second, _third = create_search_fixture(db_session)

    response = retrieval_client.get(
        "/papers",
        params={
            "limit": 1,
            "offset": 0,
            "sort": "relevance_score",
            "content_scope": "abstract",
            "extraction_status": "succeeded",
            "relevance_label": "high",
            "mri_category": "cvr",
            "analysis_status": "succeeded",
            "analysis_scope": "abstract_only",
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["total"] == 1
    assert body["items"][0]["id"] == first.id
    assert body["items"][0]["relevance_summary"]["rule_label"] == "high"
    assert body["items"][0]["analysis_availability"][0]["status"] == "succeeded"
    assert "abstract" not in body["items"][0]
    assert "extracted_text" not in str(body)


@pytest.mark.integration
def test_get_paper_detail_contents_and_chunks(
    retrieval_client: TestClient,
    db_session: Session,
) -> None:
    first, _second, _third = create_search_fixture(db_session)

    detail = retrieval_client.get(f"/papers/{first.id}")
    contents = retrieval_client.get(f"/papers/{first.id}/contents")
    chunks = retrieval_client.get(
        f"/papers/{first.id}/chunks",
        params={
            "section": "results",
            "limit": 1,
        },
    )

    assert detail.status_code == 200
    assert contents.status_code == 200
    assert chunks.status_code == 200

    detail_body = detail.json()
    contents_body = contents.json()
    chunks_body = chunks.json()

    assert detail_body["abstract"] == "Abstract for BOLD CVR MRI"
    assert detail_body["related"]["contents"] == f"/papers/{first.id}/contents"
    assert contents_body[0]["content_type"] == "abstract"
    assert "extracted_text" not in contents_body[0]
    assert chunks_body["total"] == 1
    assert "Results showed CVR change." in chunks_body["items"][0]["text"]


@pytest.mark.integration
def test_retrieval_returns_404_for_missing_resources(
    retrieval_client: TestClient,
) -> None:
    assert retrieval_client.get("/papers/999999").status_code == 404
    assert retrieval_client.get("/papers/999999/contents").status_code == 404
    assert retrieval_client.get("/papers/999999/chunks").status_code == 404


@pytest.mark.integration
def test_retrieval_validates_query_parameters(
    retrieval_client: TestClient,
) -> None:
    invalid_limit = retrieval_client.get("/papers", params={"limit": 101})
    invalid_doi = retrieval_client.get("/papers", params={"doi": "not-a-doi"})
    invalid_dates = retrieval_client.get(
        "/papers",
        params={
            "publication_date_from": "2026-01-02",
            "publication_date_to": "2026-01-01",
        },
    )

    assert invalid_limit.status_code == 422
    assert invalid_doi.status_code == 422
    assert invalid_dates.status_code == 422
