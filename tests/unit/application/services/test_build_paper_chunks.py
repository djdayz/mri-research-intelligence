from collections.abc import Sequence
from datetime import UTC, datetime

from mrinsight.application.services import (
    BuildPaperChunksService,
    ChunkWriteOutcome,
)
from mrinsight.nlp import compute_text_checksum
from mrinsight.papers import (
    ContentType,
    ExtractionStatus,
    NewPaperChunk,
    StoredPaperChunk,
    StoredPaperContent,
)


class InMemoryPaperChunkRepository:
    """In-memory repository for chunk-service tests."""

    def __init__(self) -> None:
        self._chunks: dict[
            int,
            tuple[StoredPaperChunk, ...],
        ] = {}
        self._next_id = 1

    def list_by_content(
        self,
        paper_content_id: int,
    ) -> tuple[StoredPaperChunk, ...]:
        return self._chunks.get(
            paper_content_id,
            (),
        )

    def add_many(
        self,
        chunks: Sequence[NewPaperChunk],
    ) -> tuple[StoredPaperChunk, ...]:
        now = datetime.now(UTC)
        stored_chunks: list[StoredPaperChunk] = []

        for chunk in chunks:
            stored = StoredPaperChunk(
                id=self._next_id,
                paper_id=chunk.paper_id,
                paper_content_id=(chunk.paper_content_id),
                section_type=chunk.section_type,
                heading=chunk.heading,
                sequence_number=chunk.sequence_number,
                text=chunk.text,
                start_char=chunk.start_char,
                end_char=chunk.end_char,
                paragraph_start_sequence=(chunk.paragraph_start_sequence),
                paragraph_end_sequence=(chunk.paragraph_end_sequence),
                token_count=chunk.token_count,
                page_number=chunk.page_number,
                chunker_version=chunk.chunker_version,
                created_at=now,
                updated_at=now,
            )

            self._next_id += 1
            stored_chunks.append(stored)

        if stored_chunks:
            content_id = stored_chunks[0].paper_content_id
            self._chunks[content_id] = tuple(stored_chunks)

        return tuple(stored_chunks)

    def delete_by_content(
        self,
        paper_content_id: int,
    ) -> int:
        existing = self._chunks.pop(
            paper_content_id,
            (),
        )

        return len(existing)


def make_content(
    text: str,
    *,
    content_id: int = 10,
) -> StoredPaperContent:
    """Create successful content for chunk tests."""

    now = datetime.now(UTC)

    return StoredPaperContent(
        id=content_id,
        paper_id=1,
        content_type=ContentType.ABSTRACT,
        extraction_status=ExtractionStatus.SUCCEEDED,
        extracted_text=text,
        parser_version="scientific-text-v1",
        checksum=compute_text_checksum(text),
        created_at=now,
        updated_at=now,
    )


def test_chunk_service_creates_chunks() -> None:
    repository = InMemoryPaperChunkRepository()
    service = BuildPaperChunksService(
        repository,
        max_tokens=5,
    )

    result = service.execute(
        make_content("First MRI paragraph.\n\nSecond MRI paragraph.")
    )

    assert result.outcome is ChunkWriteOutcome.CREATED
    assert len(result.chunks) == 2
    assert [chunk.sequence_number for chunk in result.chunks] == [1, 2]


def test_identical_chunks_are_not_rewritten() -> None:
    repository = InMemoryPaperChunkRepository()
    service = BuildPaperChunksService(repository)
    content = make_content("MRI reconstruction results.")

    first = service.execute(content)
    second = service.execute(content)

    assert first.outcome is ChunkWriteOutcome.CREATED
    assert second.outcome is (ChunkWriteOutcome.UNCHANGED)

    assert [chunk.id for chunk in second.chunks] == [chunk.id for chunk in first.chunks]


def test_changed_content_rebuilds_chunks() -> None:
    repository = InMemoryPaperChunkRepository()
    service = BuildPaperChunksService(repository)

    first = service.execute(make_content("Initial MRI results."))
    second = service.execute(
        make_content("Updated MRI results with external validation.")
    )

    assert first.outcome is ChunkWriteOutcome.CREATED
    assert second.outcome is ChunkWriteOutcome.REBUILT

    assert first.chunks[0].id != second.chunks[0].id
    assert second.chunks[0].text == ("Updated MRI results with external validation.")
    assert len(repository.list_by_content(10)) == 1


def test_failed_content_is_skipped_without_chunks() -> None:
    repository = InMemoryPaperChunkRepository()
    service = BuildPaperChunksService(repository)
    now = datetime.now(UTC)

    content = StoredPaperContent(
        id=10,
        paper_id=1,
        content_type=ContentType.FULL_TEXT,
        extraction_status=ExtractionStatus.FAILED,
        extracted_text=None,
        parser_version="pdf-parser-v1",
        checksum=None,
        created_at=now,
        updated_at=now,
    )

    result = service.execute(content)

    assert result.outcome is ChunkWriteOutcome.SKIPPED
    assert result.chunks == ()
