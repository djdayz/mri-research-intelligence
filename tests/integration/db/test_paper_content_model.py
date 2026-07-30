import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from mrinsight.db.models import Paper, PaperContent
from mrinsight.nlp import (
    TEXT_CLEANER_VERSION,
    clean_scientific_text,
    compute_text_checksum,
)
from mrinsight.papers import ContentType, ExtractionStatus


def create_test_paper(
    session: Session,
    *,
    doi: str,
) -> Paper:
    """Insert the minimum valid parent paper."""

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
def test_successful_abstract_content_can_be_persisted(
    db_session: Session,
) -> None:
    paper = create_test_paper(
        db_session,
        doi="10.1234/content.example",
    )

    raw_text = "  MRI\tmethods.\r\n\r\nThe RMSE was 0.20.  "
    cleaned_text = clean_scientific_text(raw_text)

    content = PaperContent(
        paper_id=paper.id,
        content_type=ContentType.ABSTRACT.value,
        extraction_status=(ExtractionStatus.SUCCEEDED.value),
        extracted_text=cleaned_text,
        parser_version=TEXT_CLEANER_VERSION,
        checksum=compute_text_checksum(cleaned_text),
    )

    db_session.add(content)
    db_session.flush()

    retrieved = db_session.execute(
        select(PaperContent).where(PaperContent.id == content.id)
    ).scalar_one()

    assert retrieved.paper_id == paper.id
    assert retrieved.extracted_text == ("MRI methods.\n\nThe RMSE was 0.20.")
    assert retrieved.checksum is not None
    assert len(retrieved.checksum) == 64


@pytest.mark.integration
def test_successful_content_requires_text_and_checksum(
    db_session: Session,
) -> None:
    paper = create_test_paper(
        db_session,
        doi="10.1234/invalid.content",
    )

    content = PaperContent(
        paper_id=paper.id,
        content_type=ContentType.ABSTRACT.value,
        extraction_status=(ExtractionStatus.SUCCEEDED.value),
        extracted_text=None,
        parser_version=TEXT_CLEANER_VERSION,
        checksum=None,
    )

    db_session.add(content)

    with pytest.raises(IntegrityError):
        db_session.flush()


@pytest.mark.integration
def test_paper_cannot_have_duplicate_content_scope(
    db_session: Session,
) -> None:
    paper = create_test_paper(
        db_session,
        doi="10.1234/duplicate.content",
    )

    text = "An MRI abstract."
    checksum = compute_text_checksum(text)

    first = PaperContent(
        paper_id=paper.id,
        content_type=ContentType.ABSTRACT.value,
        extraction_status=(ExtractionStatus.SUCCEEDED.value),
        extracted_text=text,
        parser_version=TEXT_CLEANER_VERSION,
        checksum=checksum,
    )

    second = PaperContent(
        paper_id=paper.id,
        content_type=ContentType.ABSTRACT.value,
        extraction_status=(ExtractionStatus.SUCCEEDED.value),
        extracted_text="A replacement abstract.",
        parser_version=TEXT_CLEANER_VERSION,
        checksum=compute_text_checksum("A replacement abstract."),
    )

    db_session.add(first)
    db_session.flush()
    db_session.add(second)

    with pytest.raises(IntegrityError):
        db_session.flush()
