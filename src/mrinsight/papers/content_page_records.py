from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class NewPaperContentPage:
    """One extracted page ready for persistence."""

    paper_content_id: int
    page_number: int
    text: str
    start_char: int
    end_char: int


@dataclass(frozen=True, slots=True)
class StoredPaperContentPage:
    """One persisted text-bearing page."""

    id: int
    paper_content_id: int
    page_number: int
    text: str
    start_char: int
    end_char: int
    created_at: datetime
