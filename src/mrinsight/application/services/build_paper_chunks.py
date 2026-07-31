from dataclasses import dataclass
from enum import StrEnum

from mrinsight.nlp import (
    CHUNKER_VERSION,
    build_section_chunks,
)
from mrinsight.papers import (
    ExtractionStatus,
    NewPaperChunk,
    StoredPaperChunk,
    StoredPaperContent,
)
from mrinsight.papers.repositories import (
    PaperChunkRepository,
)


class ChunkWriteOutcome(StrEnum):
    """Outcome of synchronising persisted chunks."""

    CREATED = "created"
    REBUILT = "rebuilt"
    UNCHANGED = "unchanged"
    CLEARED = "cleared"
    SKIPPED = "skipped"


@dataclass(frozen=True, slots=True)
class BuildPaperChunksResult:
    """Result of building persisted evidence chunks."""

    chunks: tuple[StoredPaperChunk, ...]
    outcome: ChunkWriteOutcome


class BuildPaperChunksService:
    """Synchronise persisted chunks with one content record."""

    def __init__(
        self,
        repository: PaperChunkRepository,
        *,
        max_tokens: int = 250,
        include_references: bool = False,
    ) -> None:
        if max_tokens < 1:
            raise ValueError("max_tokens must be at least 1.")

        self._repository = repository
        self._max_tokens = max_tokens
        self._include_references = include_references

    def execute(
        self,
        content: StoredPaperContent,
    ) -> BuildPaperChunksResult:
        """Create, rebuild, reuse or clear persisted chunks."""

        existing = self._repository.list_by_content(content.id)

        if (
            content.extraction_status is not ExtractionStatus.SUCCEEDED
            or content.extracted_text is None
        ):
            return self._clear_or_skip(
                content.id,
                existing,
            )

        detected_chunks = build_section_chunks(
            content.extracted_text,
            content_type=content.content_type,
            max_tokens=self._max_tokens,
            include_references=self._include_references,
        )

        candidates = tuple(
            NewPaperChunk(
                paper_id=content.paper_id,
                paper_content_id=content.id,
                section_type=chunk.section_type,
                heading=chunk.heading,
                sequence_number=chunk.sequence_number,
                text=chunk.text,
                start_char=chunk.start_char,
                end_char=chunk.end_char,
                paragraph_start_sequence=(chunk.paragraph_start_sequence),
                paragraph_end_sequence=(chunk.paragraph_end_sequence),
                token_count=chunk.token_count,
                page_number=None,
                chunker_version=CHUNKER_VERSION,
            )
            for chunk in detected_chunks
        )

        if not candidates:
            return self._clear_or_skip(
                content.id,
                existing,
            )

        if _chunk_sets_match(existing, candidates):
            return BuildPaperChunksResult(
                chunks=existing,
                outcome=ChunkWriteOutcome.UNCHANGED,
            )

        if existing:
            self._repository.delete_by_content(content.id)

            rebuilt = self._repository.add_many(candidates)

            return BuildPaperChunksResult(
                chunks=rebuilt,
                outcome=ChunkWriteOutcome.REBUILT,
            )

        created = self._repository.add_many(candidates)

        return BuildPaperChunksResult(
            chunks=created,
            outcome=ChunkWriteOutcome.CREATED,
        )

    def _clear_or_skip(
        self,
        paper_content_id: int,
        existing: tuple[StoredPaperChunk, ...],
    ) -> BuildPaperChunksResult:
        """Remove stale chunks or skip empty content."""

        if not existing:
            return BuildPaperChunksResult(
                chunks=(),
                outcome=ChunkWriteOutcome.SKIPPED,
            )

        self._repository.delete_by_content(paper_content_id)

        return BuildPaperChunksResult(
            chunks=(),
            outcome=ChunkWriteOutcome.CLEARED,
        )


def _chunk_sets_match(
    existing: tuple[StoredPaperChunk, ...],
    candidates: tuple[NewPaperChunk, ...],
) -> bool:
    """Return whether persisted and generated chunks are equivalent."""

    if len(existing) != len(candidates):
        return False

    return all(
        _stored_chunk_matches_candidate(
            stored,
            candidate,
        )
        for stored, candidate in zip(
            existing,
            candidates,
            strict=True,
        )
    )


def _stored_chunk_matches_candidate(
    stored: StoredPaperChunk,
    candidate: NewPaperChunk,
) -> bool:
    """Compare all reproducibility-relevant chunk fields."""

    return (
        stored.paper_id == candidate.paper_id
        and stored.paper_content_id == candidate.paper_content_id
        and stored.section_type is candidate.section_type
        and stored.heading == candidate.heading
        and stored.sequence_number == candidate.sequence_number
        and stored.text == candidate.text
        and stored.start_char == candidate.start_char
        and stored.end_char == candidate.end_char
        and stored.paragraph_start_sequence == candidate.paragraph_start_sequence
        and stored.paragraph_end_sequence == candidate.paragraph_end_sequence
        and stored.token_count == candidate.token_count
        and stored.page_number == candidate.page_number
        and stored.chunker_version == candidate.chunker_version
    )
