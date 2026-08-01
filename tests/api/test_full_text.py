from collections.abc import Iterator, Sequence
from datetime import date
from typing import cast

import pytest
from fastapi.testclient import TestClient
from httpx import Response
from pydantic import HttpUrl
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from tests.helpers.pdf_factory import build_blank_pdf, build_text_pdf

from mrinsight.api.dependencies import (
    get_bibliographic_provider,
    get_db_session,
    get_paper_content_page_repository,
)
from mrinsight.db.models import (
    PaperChunk,
    PaperContent,
    PaperContentPage,
)
from mrinsight.main import app
from mrinsight.papers import (
    ContentType,
    NewPaperContentPage,
    ResolvedPaperMetadata,
    StoredPaperContentPage,
)
from mrinsight.papers.providers import (
    BibliographicProvider,
    FakeBibliographicProvider,
)
from mrinsight.papers.repositories import (
    PaperContentPageRepository,
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
def client(
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
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


def create_parent_paper(
    client: TestClient,
) -> int:
    """Create a paper through the public ingestion endpoint."""

    paper_response = client.post(
        "/papers",
        json={"doi": "10.1234/MRI.EXAMPLE"},
    )

    assert paper_response.status_code == 201

    return int(paper_response.json()["id"])


def upload_pdf(
    client: TestClient,
    paper_id: int,
    pdf_data: bytes,
    *,
    media_type: str = "application/pdf",
) -> Response:
    """Upload PDF data to the full-text endpoint."""

    return cast(
        Response,
        client.post(
            f"/papers/{paper_id}/full-text",
            files={
                "file": (
                    "paper.pdf",
                    pdf_data,
                    media_type,
                )
            },
        ),
    )


class FailingPageRepository:
    """Repository that simulates page persistence failure."""

    def list_by_content(
        self,
        paper_content_id: int,
    ) -> tuple[StoredPaperContentPage, ...]:
        return ()

    def replace_for_content(
        self,
        paper_content_id: int,
        pages: Sequence[NewPaperContentPage],
    ) -> tuple[StoredPaperContentPage, ...]:
        raise RuntimeError("Simulated page persistence failure.")


def build_valid_pdf() -> bytes:
    """Build a two-page scientific PDF fixture."""

    return build_text_pdf(
        [
            [
                "Methods",
                "MRI data were acquired at 3 T.",
            ],
            [
                "Results",
                "RMSE decreased to 0.20.",
            ],
        ]
    )


@pytest.mark.integration
def test_full_text_upload_persists_content_pages_and_chunks(
    client: TestClient,
    db_session: Session,
) -> None:
    paper_id = create_parent_paper(client)

    response = upload_pdf(
        client,
        paper_id,
        build_valid_pdf(),
    )

    assert response.status_code == 201

    body = response.json()

    assert body["outcome"] == "created"
    assert body["extraction_status"] == "succeeded"
    assert body["analysis_scope"] == "full_text"
    assert body["page_count"] == 2
    assert body["text_page_count"] == 2
    assert body["chunk_count"] >= 2

    content = db_session.execute(
        select(PaperContent).where(
            PaperContent.paper_id == paper_id,
            PaperContent.content_type == ContentType.FULL_TEXT.value,
        )
    ).scalar_one()

    pages = (
        db_session.execute(
            select(PaperContentPage)
            .where(PaperContentPage.paper_content_id == content.id)
            .order_by(PaperContentPage.page_number)
        )
        .scalars()
        .all()
    )
    chunks = (
        db_session.execute(
            select(PaperChunk)
            .where(PaperChunk.paper_content_id == content.id)
            .order_by(PaperChunk.sequence_number)
        )
        .scalars()
        .all()
    )

    assert content.extraction_status == "succeeded"
    assert len(pages) == 2
    assert chunks
    assert all(chunk.paper_content_id == content.id for chunk in chunks)
    assert all(chunk.page_number is not None for chunk in chunks)
    assert all(chunk.end_page_number is not None for chunk in chunks)


@pytest.mark.integration
def test_repeated_full_text_upload_is_unchanged(
    client: TestClient,
) -> None:
    paper_id = create_parent_paper(client)
    pdf_data = build_valid_pdf()

    first = upload_pdf(
        client,
        paper_id,
        pdf_data,
    )
    second = upload_pdf(
        client,
        paper_id,
        pdf_data,
    )

    assert first.status_code == 201
    assert second.status_code == 200
    assert second.json()["outcome"] == "unchanged"


@pytest.mark.integration
def test_full_text_upload_rejects_unsupported_media_type(
    client: TestClient,
) -> None:
    paper_id = create_parent_paper(client)

    response = upload_pdf(
        client,
        paper_id,
        b"plain text",
        media_type="text/plain",
    )

    assert response.status_code == 415


@pytest.mark.integration
def test_full_text_upload_rejects_missing_paper(
    client: TestClient,
) -> None:
    response = upload_pdf(
        client,
        999999,
        build_valid_pdf(),
    )

    assert response.status_code == 404


@pytest.mark.integration
def test_textless_pdf_persists_failed_full_text(
    client: TestClient,
    db_session: Session,
) -> None:
    paper_id = create_parent_paper(client)

    response = upload_pdf(
        client,
        paper_id,
        build_blank_pdf(),
    )

    assert response.status_code == 422

    body = response.json()

    assert body["outcome"] == "failed"
    assert body["extraction_status"] == "failed"
    assert body["analysis_scope"] == "abstract_only"
    assert body["text_page_count"] == 0
    assert body["chunk_count"] == 0
    assert body["error"] is not None

    failed_content = db_session.execute(
        select(PaperContent).where(
            PaperContent.paper_id == paper_id,
            PaperContent.content_type == ContentType.FULL_TEXT.value,
        )
    ).scalar_one()

    assert failed_content.extraction_status == "failed"
    assert failed_content.extraction_error is not None


@pytest.mark.integration
def test_full_text_page_failure_rolls_back_full_text_records(
    client: TestClient,
    db_session: Session,
) -> None:
    paper_id = create_parent_paper(client)

    def override_page_repository() -> PaperContentPageRepository:
        return FailingPageRepository()

    app.dependency_overrides[get_paper_content_page_repository] = (
        override_page_repository
    )

    with pytest.raises(
        RuntimeError,
        match="Simulated page persistence failure",
    ):
        upload_pdf(
            client,
            paper_id,
            build_valid_pdf(),
        )

    full_text_content_count = db_session.scalar(
        select(func.count())
        .select_from(PaperContent)
        .where(
            PaperContent.paper_id == paper_id,
            PaperContent.content_type == ContentType.FULL_TEXT.value,
        )
    )
    page_count = db_session.scalar(select(func.count()).select_from(PaperContentPage))
    full_text_chunk_count = db_session.scalar(
        select(func.count())
        .select_from(PaperChunk)
        .join(
            PaperContent,
            PaperContent.id == PaperChunk.paper_content_id,
        )
        .where(
            PaperContent.paper_id == paper_id,
            PaperContent.content_type == ContentType.FULL_TEXT.value,
        )
    )
    abstract_content_count = db_session.scalar(
        select(func.count())
        .select_from(PaperContent)
        .where(
            PaperContent.paper_id == paper_id,
            PaperContent.content_type == ContentType.ABSTRACT.value,
        )
    )

    assert full_text_content_count == 0
    assert page_count == 0
    assert full_text_chunk_count == 0
    assert abstract_content_count == 1
