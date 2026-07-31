import pytest
from sqlalchemy.orm import Session

from mrinsight.db.models import Paper, PaperContent
from mrinsight.db.repositories import (
    SqlAlchemyPaperChunkRepository,
)
from mrinsight.nlp import (
    CHUNKER_VERSION,
    TEXT_CLEANER_VERSION,
    compute_text_checksum,
)
from mrinsight.papers import (
    ContentType,
    ExtractionStatus,
    NewPaperChunk,
    SectionType,
)


def create_parent_content(
    session: Session,
    *,
    doi: str,
) -> tuple[Paper, PaperContent]:
    """Insert one parent paper and content record."""

    paper = Paper(
        doi=doi,
        normalized_doi=doi,
        title="Example MRI Paper",
        normalized_title="example mri paper",
        ingestion_source="test",
    )

    session.add(paper)
    session.flush()

    text = "MRI methods.\n\nThe model reduced RMSE."

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


def make_chunk(
    *,
    paper_id: int,
    paper_content_id: int,
    sequence_number: int,
    text: str,
    start_char: int,
) -> NewPaperChunk:
    """Create valid chunk data."""

    return NewPaperChunk(
        paper_id=paper_id,
        paper_content_id=paper_content_id,
        section_type=SectionType.ABSTRACT,
        heading=None,
        sequence_number=sequence_number,
        text=text,
        start_char=start_char,
        end_char=start_char + len(text),
        paragraph_start_sequence=sequence_number,
        paragraph_end_sequence=sequence_number,
        token_count=len(text.split()),
        page_number=None,
        chunker_version=CHUNKER_VERSION,
    )


@pytest.mark.integration
def test_repository_adds_and_lists_ordered_chunks(
    db_session: Session,
) -> None:
    paper, content = create_parent_content(
        db_session,
        doi="10.1234/chunk.repository",
    )
    repository = SqlAlchemyPaperChunkRepository(db_session)

    second = make_chunk(
        paper_id=paper.id,
        paper_content_id=content.id,
        sequence_number=2,
        text="The model reduced RMSE.",
        start_char=14,
    )
    first = make_chunk(
        paper_id=paper.id,
        paper_content_id=content.id,
        sequence_number=1,
        text="MRI methods.",
        start_char=0,
    )

    repository.add_many([second, first])

    retrieved = repository.list_by_content(content.id)

    assert [chunk.sequence_number for chunk in retrieved] == [1, 2]


@pytest.mark.integration
def test_repository_deletes_chunks_by_content(
    db_session: Session,
) -> None:
    paper, content = create_parent_content(
        db_session,
        doi="10.1234/chunk.delete",
    )
    repository = SqlAlchemyPaperChunkRepository(db_session)

    repository.add_many(
        [
            make_chunk(
                paper_id=paper.id,
                paper_content_id=content.id,
                sequence_number=1,
                text="MRI methods.",
                start_char=0,
            )
        ]
    )

    deleted_count = repository.delete_by_content(content.id)

    assert deleted_count == 1
    assert repository.list_by_content(content.id) == ()
