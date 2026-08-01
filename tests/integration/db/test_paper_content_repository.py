import pytest
from sqlalchemy.orm import Session

from mrinsight.db.models import Paper
from mrinsight.db.repositories import (
    SqlAlchemyPaperContentRepository,
)
from mrinsight.nlp import compute_text_checksum
from mrinsight.papers import (
    ContentType,
    ExtractionStatus,
    NewPaperContent,
)
from mrinsight.papers.repositories import (
    PaperContentNotFoundError,
)


def create_parent_paper(
    session: Session,
    *,
    doi: str,
) -> Paper:
    """Insert a parent paper for repository tests."""

    paper = Paper(
        doi=doi,
        normalized_doi=doi,
        title="Example MRI Paper",
        normalized_title="example mri paper",
        ingestion_source="test",
    )

    session.add(paper)
    session.flush()

    return paper


@pytest.mark.integration
def test_content_repository_adds_and_retrieves_content(
    db_session: Session,
) -> None:
    paper = create_parent_paper(
        db_session,
        doi="10.1234/content.repository",
    )
    repository = SqlAlchemyPaperContentRepository(db_session)

    text = "An MRI abstract."

    created = repository.add(
        NewPaperContent(
            paper_id=paper.id,
            content_type=ContentType.ABSTRACT,
            extraction_status=(ExtractionStatus.SUCCEEDED),
            extracted_text=text,
            parser_version="scientific-text-v1",
            checksum=compute_text_checksum(text),
        )
    )

    retrieved = repository.get_by_paper_and_type(
        paper.id,
        ContentType.ABSTRACT,
    )

    assert retrieved is not None
    assert retrieved.id == created.id
    assert retrieved.content_type is ContentType.ABSTRACT
    assert retrieved.extraction_status is ExtractionStatus.SUCCEEDED
    assert retrieved.extracted_text == text


@pytest.mark.integration
def test_content_repository_updates_existing_extraction(
    db_session: Session,
) -> None:
    paper = create_parent_paper(
        db_session,
        doi="10.1234/content.update",
    )
    repository = SqlAlchemyPaperContentRepository(db_session)

    failed = repository.add(
        NewPaperContent(
            paper_id=paper.id,
            content_type=ContentType.ABSTRACT,
            extraction_status=ExtractionStatus.FAILED,
            extracted_text=None,
            parser_version="scientific-text-v0",
            checksum=None,
            extraction_error="Simulated extraction failure.",
        )
    )

    replacement = "Recovered MRI abstract."

    updated = repository.update_extraction(
        failed.id,
        extraction_status=ExtractionStatus.SUCCEEDED,
        extracted_text=replacement,
        parser_version="scientific-text-v1",
        checksum=compute_text_checksum(replacement),
    )

    assert updated.id == failed.id
    assert updated.extraction_status is ExtractionStatus.SUCCEEDED
    assert updated.extracted_text == replacement
    assert updated.checksum is not None


@pytest.mark.integration
def test_content_repository_rejects_unknown_content_id(
    db_session: Session,
) -> None:
    repository = SqlAlchemyPaperContentRepository(db_session)

    with pytest.raises(
        PaperContentNotFoundError,
        match="999999",
    ):
        repository.update_extraction(
            999999,
            extraction_status=ExtractionStatus.SUCCEEDED,
            extracted_text="Missing content.",
            parser_version="scientific-text-v1",
            checksum=compute_text_checksum("Missing content."),
        )
