from collections.abc import Sequence
from typing import Any, cast

from sqlalchemy import delete, select
from sqlalchemy.engine import CursorResult
from sqlalchemy.orm import Session

from mrinsight.db.models import PaperChunk
from mrinsight.db.repositories.conflicts import add_with_conflict_recovery
from mrinsight.papers import (
    NewPaperChunk,
    SectionType,
    StoredPaperChunk,
)


class SqlAlchemyPaperChunkRepository:
    """Persist paper chunks using SQLAlchemy."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_by_content(
        self,
        paper_content_id: int,
    ) -> tuple[StoredPaperChunk, ...]:
        """Return chunks ordered by sequence number."""

        statement = (
            select(PaperChunk)
            .where(PaperChunk.paper_content_id == paper_content_id)
            .order_by(PaperChunk.sequence_number)
        )

        models = self._session.execute(statement).scalars()

        return tuple(self._to_stored_chunk(model) for model in models)

    def add_many(
        self,
        chunks: Sequence[NewPaperChunk],
    ) -> tuple[StoredPaperChunk, ...]:
        """Insert a complete chunk set without committing."""

        if not chunks:
            return ()

        def insert() -> tuple[StoredPaperChunk, ...]:
            models = [
                PaperChunk(
                    paper_id=chunk.paper_id,
                    paper_content_id=chunk.paper_content_id,
                    section=chunk.section_type.value,
                    heading=chunk.heading,
                    sequence_number=chunk.sequence_number,
                    text=chunk.text,
                    start_char=chunk.start_char,
                    end_char=chunk.end_char,
                    paragraph_start_sequence=(chunk.paragraph_start_sequence),
                    paragraph_end_sequence=(chunk.paragraph_end_sequence),
                    token_count=chunk.token_count,
                    page_number=chunk.page_number,
                    end_page_number=chunk.end_page_number,
                    chunker_version=chunk.chunker_version,
                )
                for chunk in chunks
            ]

            self._session.add_all(models)
            self._session.flush()

            for model in models:
                self._session.refresh(model)

            return tuple(self._to_stored_chunk(model) for model in models)

        return add_with_conflict_recovery(
            self._session,
            insert=insert,
            recover=lambda: self.list_by_content(chunks[0].paper_content_id),
            message="A duplicate chunk sequence insert could not be recovered.",
        )

    def delete_by_content(
        self,
        paper_content_id: int,
    ) -> int:
        """Delete all chunks for one content record."""

        statement = delete(PaperChunk).where(
            PaperChunk.paper_content_id == paper_content_id
        )

        result = cast(
            CursorResult[Any],
            self._session.execute(statement),
        )
        self._session.flush()

        return result.rowcount or 0

    @staticmethod
    def _to_stored_chunk(
        model: PaperChunk,
    ) -> StoredPaperChunk:
        """Translate an ORM model into an application value."""

        return StoredPaperChunk(
            id=model.id,
            paper_id=model.paper_id,
            paper_content_id=model.paper_content_id,
            section_type=SectionType(model.section),
            heading=model.heading,
            sequence_number=model.sequence_number,
            text=model.text,
            start_char=model.start_char,
            end_char=model.end_char,
            paragraph_start_sequence=(model.paragraph_start_sequence),
            paragraph_end_sequence=(model.paragraph_end_sequence),
            token_count=model.token_count,
            page_number=model.page_number,
            end_page_number=model.end_page_number,
            chunker_version=model.chunker_version,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
