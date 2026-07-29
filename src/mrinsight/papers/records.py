from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True, slots=True)
class NewPaper:
    """Paper data ready to be persisted."""

    doi: str | None
    normalized_doi: str | None
    title: str
    normalized_title: str
    abstract: str | None
    journal: str | None
    publication_date: date | None
    source_url: str | None
    ingestion_source: str
    provider_record_id: str | None


@dataclass(frozen=True, slots=True)
class StoredPaper:
    """Paper data returned from persistence."""

    id: int
    doi: str | None
    normalized_doi: str | None
    title: str
    normalized_title: str
    abstract: str | None
    journal: str | None
    publication_date: date | None
    source_url: str | None
    ingestion_source: str
    provider_record_id: str | None
    created_at: datetime
    updated_at: datetime
