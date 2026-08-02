from collections.abc import Iterator
from datetime import date

import pytest
from fastapi.testclient import TestClient
from pydantic import HttpUrl
from sqlalchemy.orm import Session

from mrinsight.analysis import FakeLLMMode, FakeLLMProvider, LLMProvider
from mrinsight.api.dependencies import (
    get_bibliographic_provider,
    get_db_session,
    get_llm_provider,
)
from mrinsight.db.models import Paper
from mrinsight.main import app
from mrinsight.papers import ResolvedPaperMetadata
from mrinsight.papers.providers import (
    BibliographicProvider,
    FakeBibliographicProvider,
)


def make_metadata_record() -> ResolvedPaperMetadata:
    """Create metadata returned by the fake provider."""

    return ResolvedPaperMetadata(
        doi="10.1234/analysis.api",
        title="BOLD MRI analysis",
        abstract="MRI methods reported 2.5 units.",
        journal="Journal of MRI Research",
        publication_date=date(2026, 3, 15),
        source_url=HttpUrl("https://example.org/papers/analysis-api"),
        authors=("Alice Smith", "Bob Jones"),
        provider_name="fake",
        provider_record_id="record-analysis",
    )


@pytest.fixture
def analysis_client(
    db_session: Session,
) -> Iterator[TestClient]:
    """Create an API client with deterministic providers."""

    provider = FakeBibliographicProvider([make_metadata_record()])
    llm_provider = FakeLLMProvider(mode=FakeLLMMode.VALID)

    def override_db_session() -> Iterator[Session]:
        try:
            yield db_session
            db_session.commit()
        except Exception:
            db_session.rollback()
            raise

    def override_provider() -> BibliographicProvider:
        return provider

    def override_llm_provider() -> LLMProvider:
        return llm_provider

    app.dependency_overrides[get_db_session] = override_db_session
    app.dependency_overrides[get_bibliographic_provider] = override_provider
    app.dependency_overrides[get_llm_provider] = override_llm_provider

    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()


def create_parent_paper(
    client: TestClient,
) -> int:
    """Create a paper through the public ingestion endpoint."""

    response = client.post(
        "/papers",
        json={"doi": "10.1234/ANALYSIS.API"},
    )

    assert response.status_code == 201

    return int(response.json()["id"])


@pytest.mark.integration
def test_post_analysis_creates_and_caches_fake_llm_analysis(
    analysis_client: TestClient,
) -> None:
    paper_id = create_parent_paper(analysis_client)

    first = analysis_client.post(f"/papers/{paper_id}/analysis")
    second = analysis_client.post(f"/papers/{paper_id}/analysis")

    assert first.status_code == 201
    assert second.status_code == 200

    first_body = first.json()
    second_body = second.json()

    assert first_body["cached"] is False
    assert first_body["outcome"] == "created"
    assert first_body["status"] == "succeeded"
    assert first_body["analysis"]["analysis_scope"] == "abstract_only"
    assert first_body["evidence_references"]
    assert second_body["cached"] is True
    assert second_body["outcome"] == "cached"
    assert second_body["id"] == first_body["id"]


@pytest.mark.integration
def test_get_analysis_by_paper_and_id(
    analysis_client: TestClient,
) -> None:
    paper_id = create_parent_paper(analysis_client)
    created = analysis_client.post(f"/papers/{paper_id}/analysis").json()

    by_paper = analysis_client.get(f"/papers/{paper_id}/analysis")
    by_id = analysis_client.get(f"/analyses/{created['id']}")

    assert by_paper.status_code == 200
    assert by_id.status_code == 200
    assert by_paper.json()[0]["id"] == created["id"]
    assert by_id.json()["id"] == created["id"]


@pytest.mark.integration
def test_post_analysis_returns_404_for_missing_paper(
    analysis_client: TestClient,
) -> None:
    response = analysis_client.post("/papers/999999/analysis")

    assert response.status_code == 404


@pytest.mark.integration
def test_post_analysis_returns_422_when_no_content_exists(
    analysis_client: TestClient,
    db_session: Session,
) -> None:
    paper = Paper(
        doi="10.1234/no.content",
        normalized_doi="10.1234/no.content",
        title="Paper without content",
        normalized_title="paper without content",
        abstract=None,
        ingestion_source="test",
    )
    db_session.add(paper)
    db_session.flush()

    response = analysis_client.post(f"/papers/{paper.id}/analysis")

    assert response.status_code == 422


@pytest.mark.integration
def test_post_analysis_distinguishes_provider_failure(
    analysis_client: TestClient,
) -> None:
    def override_llm_provider() -> LLMProvider:
        return FakeLLMProvider(mode=FakeLLMMode.FAILURE)

    app.dependency_overrides[get_llm_provider] = override_llm_provider
    paper_id = create_parent_paper(analysis_client)

    response = analysis_client.post(f"/papers/{paper_id}/analysis")

    assert response.status_code == 503
    assert response.json()["outcome"] == "provider_failed"
    assert response.json()["status"] == "failed"
    assert response.json()["validation_errors"]
