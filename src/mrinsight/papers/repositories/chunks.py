from collections.abc import Sequence
from typing import Protocol

from mrinsight.papers.chunk_records import (
    NewPaperChunk,
    StoredPaperChunk,
)


class PaperChunkRepository(Protocol):
    """Persistence contract for scientific evidence chunks."""

    def list_by_content(
        self,
        paper_content_id: int,
    ) -> tuple[StoredPaperChunk, ...]:
        """Return chunks ordered by sequence number."""

        ...

    def add_many(
        self,
        chunks: Sequence[NewPaperChunk],
    ) -> tuple[StoredPaperChunk, ...]:
        """Persist a complete chunk set without committing."""

        ...

    def delete_by_content(
        self,
        paper_content_id: int,
    ) -> int:
        """Delete all chunks derived from one content record."""

        ...
