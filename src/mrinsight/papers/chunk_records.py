from dataclasses import dataclass
from datetime import datetime

from mrinsight.papers.content import SectionType


@dataclass(frozen=True, slots=True)
class NewPaperChunk:
    """One evidence chunk ready to be persisted."""

    paper_id: int
    paper_content_id: int
    section_type: SectionType
    heading: str | None
    sequence_number: int
    text: str
    start_char: int
    end_char: int
    paragraph_start_sequence: int
    paragraph_end_sequence: int
    token_count: int
    page_number: int | None
    chunker_version: str


@dataclass(frozen=True, slots=True)
class StoredPaperChunk:
    """One persisted scientific evidence chunk."""

    id: int
    paper_id: int
    paper_content_id: int
    section_type: SectionType
    heading: str | None
    sequence_number: int
    text: str
    start_char: int
    end_char: int
    paragraph_start_sequence: int
    paragraph_end_sequence: int
    token_count: int
    page_number: int | None
    chunker_version: str
    created_at: datetime
    updated_at: datetime
