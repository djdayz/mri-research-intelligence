from datetime import date

import pytest
from sqlalchemy.orm import Session

from mrinsight.db.repositories import (
    SqlAlchemyPaperRepository,
)
from mrinsight.papers import NewPaper


def make_new_paper() -> NewPaper:
    """Create valid paper data for repository tests."""

    return NewPaper(
        doi="10.1234/repository.example",
        normalized_doi="10.1234/repository.example",
        title="Deep Learning for MRI Reconstruction",
        normalized_title=("deep learning for mri reconstruction"),
        abstract="An MRI reconstruction study.",
        journal="Journal of MRI Research",
        publication_date=date(2026, 3, 15),
        source_url=("https://example.org/papers/repository-example"),
        ingestion_source="fake",
        provider_record_id="record-001",
    )


@pytest.mark.integration
def test_repository_adds_and_retrieves_paper(
    db_session: Session,
) -> None:
    repository = SqlAlchemyPaperRepository(db_session)

    created = repository.add(make_new_paper())

    db_session.commit()

    retrieved = repository.get_by_normalized_doi("10.1234/repository.example")

    assert created.id > 0
    assert retrieved is not None
    assert retrieved.id == created.id
    assert retrieved.title == ("Deep Learning for MRI Reconstruction")
    assert retrieved.journal == "Journal of MRI Research"
    assert retrieved.ingestion_source == "fake"


@pytest.mark.integration
def test_repository_returns_none_for_unknown_doi(
    db_session: Session,
) -> None:
    repository = SqlAlchemyPaperRepository(db_session)

    result = repository.get_by_normalized_doi("10.9999/missing.repository.paper")

    assert result is None
