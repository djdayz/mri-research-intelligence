from collections.abc import Iterator
from datetime import date

import pytest
from fastapi.testclient import TestClient
from pydantic import HttpUrl
from sqlalchemy.orm import Session

from mrinsight.api.dependencies import (
    get_bibliographic_provider,
    get_db_session,
)
from mrinsight.main import app
from mrinsight.papers import ResolvedPaperMetadata
from mrinsight.papers.providers import (
    BibliographicProvider,
    BibliographicProviderUnavailableError,
    FakeBibliographicProvider,
)


def make_metadata_record() -> ResolvedPaperMetadata:
    """Create metadata returned by the fake provider."""

    return ResolvedPaperMetadata(
        doi="10.1234/mri.example",
        title="Deep Learning for MRI Reconstruction",
        abstract="An MRI reconstruction study.",
        journal="Journal of MRI Research",
        publication_date=date(2026, 3, 15),
        source_url=HttpUrl("https://example.org/papers/mri-example"),
        authors=("Alice Smith", "Bob Jones"),
        provider_name="fake",
        provider_record_id="record-001",
    )


@pytest.fixture
def paper_client(
    db_session: Session,
) -> Iterator[TestClient]:
    """Create an API client with deterministic dependencies."""

    provider = FakeBibliographicProvider([make_metadata_record()])

    def override_db_session() -> Iterator[Session]:
        try:
            yield db_session
            db_session.commit()
        except Exception:
            db_session.rollback()
            raise

    def override_provider() -> BibliographicProvider:
        return provider

    app.dependency_overrides[get_db_session] = override_db_session
    app.dependency_overrides[get_bibliographic_provider] = override_provider

    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()


@pytest.mark.integration
def test_post_papers_creates_new_paper(
    paper_client: TestClient,
) -> None:
    response = paper_client.post(
        "/papers",
        json={"doi": ("https://doi.org/10.1234/MRI.EXAMPLE")},
    )

    assert response.status_code == 201

    body = response.json()

    assert body["created"] is True
    assert body["doi"] == "10.1234/mri.example"
    assert body["normalized_doi"] == ("10.1234/mri.example")
    assert body["title"] == ("Deep Learning for MRI Reconstruction")
    assert body["normalized_title"] == ("deep learning for mri reconstruction")
    assert body["ingestion_source"] == "fake"
    assert isinstance(body["id"], int)


@pytest.mark.integration
def test_post_papers_reuses_existing_paper(
    paper_client: TestClient,
) -> None:
    first_response = paper_client.post(
        "/papers",
        json={"doi": "10.1234/MRI.EXAMPLE"},
    )
    second_response = paper_client.post(
        "/papers",
        json={"doi": ("https://doi.org/10.1234/mri.example")},
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 200

    first_body = first_response.json()
    second_body = second_response.json()

    assert first_body["created"] is True
    assert second_body["created"] is False
    assert second_body["id"] == first_body["id"]


@pytest.mark.integration
def test_post_papers_returns_404_for_unknown_doi(
    paper_client: TestClient,
) -> None:
    response = paper_client.post(
        "/papers",
        json={"doi": "10.9999/missing.paper"},
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": ("No bibliographic record was found for this DOI.")
    }


@pytest.mark.integration
def test_post_papers_rejects_invalid_doi(
    paper_client: TestClient,
) -> None:
    response = paper_client.post(
        "/papers",
        json={"doi": "not-a-doi"},
    )

    assert response.status_code == 422


class UnavailableProvider:
    """Provider test double that simulates an outage."""

    @property
    def name(self) -> str:
        return "unavailable-test-provider"

    def resolve_by_doi(
        self,
        doi: str,
    ) -> ResolvedPaperMetadata:
        raise BibliographicProviderUnavailableError("Simulated provider outage.")


@pytest.mark.integration
def test_post_papers_returns_503_for_provider_outage(
    paper_client: TestClient,
) -> None:
    def override_provider() -> BibliographicProvider:
        return UnavailableProvider()

    app.dependency_overrides[get_bibliographic_provider] = override_provider

    response = paper_client.post(
        "/papers",
        json={"doi": "10.1234/provider.outage"},
    )

    assert response.status_code == 503
    assert response.json() == {"detail": "The bibliographic provider is unavailable."}


@pytest.mark.integration
def test_post_papers_rejects_unexpected_fields(
    paper_client: TestClient,
) -> None:
    response = paper_client.post(
        "/papers",
        json={
            "doi": "10.1234/mri.example",
            "force": True,
        },
    )

    assert response.status_code == 422
