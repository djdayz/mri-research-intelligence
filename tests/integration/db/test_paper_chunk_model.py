import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from mrinsight.db.models import (
    Paper,
    PaperChunk,
    PaperContent,
)
from mrinsight.nlp import (
    CHUNKER_VERSION,
    TEXT_CLEANER_VERSION,
    compute_text_checksum,
)
from mrinsight.papers import (
    ContentType,
    ExtractionStatus,
    SectionType,
)


def create_parent_content(
    session: Session,
    *,
    doi: str,
) -> tuple[Paper, PaperContent]:
    """Insert a paper and one successful abstract content row."""

    paper = Paper(
        doi=doi,
        normalized_doi=doi,
        title="Example MRI Paper",
        normalized_title="example mri paper",
        ingestion_source="test",
    )

    session.add(paper)
    session.flush()

    text = "An MRI abstract with results."

    content = PaperContent(
        paper_id=paper.id,
        content_type=ContentType.ABSTRACT.value,
        extraction_status=(ExtractionStatus.SUCCEEDED.value),
        extracted_text=text,
        parser_version=TEXT_CLEANER_VERSION,
        checksum=compute_text_checksum(text),
    )

    session.add(content)
    session.flush()

    return paper, content


@pytest.mark.integration
def test_valid_paper_chunk_can_be_persisted(
    db_session: Session,
) -> None:
    paper, content = create_parent_content(
        db_session,
        doi="10.1234/chunk.valid",
    )

    chunk = PaperChunk(
        paper_id=paper.id,
        paper_content_id=content.id,
        section=SectionType.ABSTRACT.value,
        heading=None,
        sequence_number=1,
        text="An MRI abstract with results.",
        start_char=0,
        end_char=29,
        paragraph_start_sequence=1,
        paragraph_end_sequence=1,
        token_count=5,
        page_number=None,
        chunker_version=CHUNKER_VERSION,
    )

    db_session.add(chunk)
    db_session.flush()

    assert chunk.id > 0


@pytest.mark.integration
def test_duplicate_chunk_sequence_is_rejected(
    db_session: Session,
) -> None:
    paper, content = create_parent_content(
        db_session,
        doi="10.1234/chunk.duplicate",
    )

    first = PaperChunk(
        paper_id=paper.id,
        paper_content_id=content.id,
        section=SectionType.ABSTRACT.value,
        sequence_number=1,
        text="First chunk.",
        start_char=0,
        end_char=12,
        paragraph_start_sequence=1,
        paragraph_end_sequence=1,
        token_count=2,
        chunker_version=CHUNKER_VERSION,
    )

    second = PaperChunk(
        paper_id=paper.id,
        paper_content_id=content.id,
        section=SectionType.ABSTRACT.value,
        sequence_number=1,
        text="Second chunk.",
        start_char=13,
        end_char=26,
        paragraph_start_sequence=2,
        paragraph_end_sequence=2,
        token_count=2,
        chunker_version=CHUNKER_VERSION,
    )

    db_session.add(first)
    db_session.flush()
    db_session.add(second)

    with pytest.raises(IntegrityError):
        db_session.flush()


@pytest.mark.integration
def test_invalid_character_range_is_rejected(
    db_session: Session,
) -> None:
    paper, content = create_parent_content(
        db_session,
        doi="10.1234/chunk.offset",
    )

    chunk = PaperChunk(
        paper_id=paper.id,
        paper_content_id=content.id,
        section=SectionType.ABSTRACT.value,
        sequence_number=1,
        text="Invalid range.",
        start_char=20,
        end_char=10,
        paragraph_start_sequence=1,
        paragraph_end_sequence=1,
        token_count=2,
        chunker_version=CHUNKER_VERSION,
    )

    db_session.add(chunk)

    with pytest.raises(IntegrityError):
        db_session.flush()
