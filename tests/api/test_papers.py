from collections.abc import Iterator, Sequence
from datetime import date

import pytest
from fastapi.testclient import TestClient
from pydantic import HttpUrl
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from mrinsight.api.dependencies import (
    get_bibliographic_provider,
    get_db_session,
    get_paper_chunk_repository,
    get_paper_content_repository,
)
from mrinsight.db.models import (
    Paper,
    PaperChunk,
    PaperContent,
)
from mrinsight.main import app
from mrinsight.papers import (
    ContentType,
    ExtractionStatus,
    NewPaperChunk,
    NewPaperContent,
    ResolvedPaperMetadata,
    SectionType,
    StoredPaperChunk,
    StoredPaperContent,
)
from mrinsight.papers.providers import (
    BibliographicProvider,
    BibliographicProviderUnavailableError,
    FakeBibliographicProvider,
)
from mrinsight.papers.repositories import (
    PaperChunkRepository,
    PaperContentRepository,
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
    db_session: Session,
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

    content_count = db_session.scalar(
        select(func.count())
        .select_from(PaperContent)
        .where(
            PaperContent.paper_id == first_body["id"],
            PaperContent.content_type == ContentType.ABSTRACT.value,
        )
    )

    assert content_count == 1

    chunk_count = db_session.scalar(
        select(func.count())
        .select_from(PaperChunk)
        .where(
            PaperChunk.paper_id == first_body["id"],
        )
    )

    assert chunk_count == 1


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
        "detail": ("No bibliographic record was found by the configured provider.")
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


class FailingPaperContentRepository:
    """Repository that simulates a content write failure."""

    def get_by_paper_and_type(
        self,
        paper_id: int,
        content_type: ContentType,
    ) -> StoredPaperContent | None:
        return None

    def add(
        self,
        content: NewPaperContent,
    ) -> StoredPaperContent:
        raise RuntimeError("Simulated content persistence failure.")

    def update_extraction(
        self,
        content_id: int,
        *,
        extraction_status: ExtractionStatus,
        extracted_text: str | None,
        parser_version: str,
        checksum: str | None,
    ) -> StoredPaperContent:
        raise RuntimeError("Simulated content persistence failure.")


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


@pytest.mark.integration
def test_content_failure_rolls_back_paper_insert(
    paper_client: TestClient,
    db_session: Session,
) -> None:
    def override_content_repository() -> PaperContentRepository:
        return FailingPaperContentRepository()

    app.dependency_overrides[get_paper_content_repository] = override_content_repository

    with pytest.raises(
        RuntimeError,
        match="Simulated content persistence failure",
    ):
        paper_client.post(
            "/papers",
            json={"doi": "10.1234/MRI.EXAMPLE"},
        )

    paper_count = db_session.scalar(
        select(func.count())
        .select_from(Paper)
        .where(
            Paper.normalized_doi == "10.1234/mri.example",
        )
    )

    assert paper_count == 0


@pytest.mark.integration
def test_post_papers_persists_abstract_evidence(
    paper_client: TestClient,
    db_session: Session,
) -> None:
    response = paper_client.post(
        "/papers",
        json={"doi": "10.1234/MRI.EXAMPLE"},
    )

    assert response.status_code == 201

    paper_id = response.json()["id"]

    content = db_session.execute(
        select(PaperContent).where(
            PaperContent.paper_id == paper_id,
            PaperContent.content_type == ContentType.ABSTRACT.value,
        )
    ).scalar_one()

    assert content.extraction_status == (ExtractionStatus.SUCCEEDED.value)
    assert content.extracted_text == ("An MRI reconstruction study.")
    assert content.checksum is not None
    assert len(content.checksum) == 64

    chunks = (
        db_session.execute(
            select(PaperChunk)
            .where(PaperChunk.paper_id == paper_id)
            .order_by(PaperChunk.sequence_number)
        )
        .scalars()
        .all()
    )

    assert len(chunks) == 1
    assert chunks[0].paper_content_id == content.id
    assert chunks[0].section == SectionType.ABSTRACT.value
    assert chunks[0].text == ("An MRI reconstruction study.")
    assert chunks[0].chunker_version == ("section-paragraph-v1")


class FailingPaperChunkRepository:
    """Repository that simulates chunk persistence failure."""

    def list_by_content(
        self,
        paper_content_id: int,
    ) -> tuple[StoredPaperChunk, ...]:
        return ()

    def add_many(
        self,
        chunks: Sequence[NewPaperChunk],
    ) -> tuple[StoredPaperChunk, ...]:
        raise RuntimeError("Simulated chunk persistence failure.")

    def delete_by_content(
        self,
        paper_content_id: int,
    ) -> int:
        return 0


@pytest.mark.integration
def test_chunk_failure_rolls_back_paper_and_content(
    paper_client: TestClient,
    db_session: Session,
) -> None:
    def override_chunk_repository() -> PaperChunkRepository:
        return FailingPaperChunkRepository()

    app.dependency_overrides[get_paper_chunk_repository] = override_chunk_repository

    with pytest.raises(
        RuntimeError,
        match="Simulated chunk persistence failure",
    ):
        paper_client.post(
            "/papers",
            json={"doi": "10.1234/MRI.EXAMPLE"},
        )

    paper_count = db_session.scalar(
        select(func.count())
        .select_from(Paper)
        .where(Paper.normalized_doi == "10.1234/mri.example")
    )

    content_count = db_session.scalar(select(func.count()).select_from(PaperContent))

    chunk_count = db_session.scalar(select(func.count()).select_from(PaperChunk))

    assert paper_count == 0
    assert content_count == 0
    assert chunk_count == 0
