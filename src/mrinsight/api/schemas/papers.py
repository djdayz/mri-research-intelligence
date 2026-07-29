from datetime import date, datetime

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    field_validator,
)

from mrinsight.application.services import IngestPaperResult
from mrinsight.papers import normalize_doi


class IngestPaperRequest(BaseModel):
    """Request body for DOI-based paper ingestion."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    doi: str = Field(min_length=1)

    @field_validator("doi")
    @classmethod
    def normalize_requested_doi(cls, value: str) -> str:
        """Validate and canonicalise the submitted DOI."""

        return normalize_doi(value)


class IngestPaperResponse(BaseModel):
    """Paper metadata returned after DOI ingestion."""

    id: int
    doi: str | None
    normalized_doi: str | None
    title: str
    normalized_title: str
    abstract: str | None
    journal: str | None
    publication_date: date | None
    source_url: HttpUrl | None
    ingestion_source: str
    provider_record_id: str | None
    created_at: datetime
    updated_at: datetime
    created: bool

    @classmethod
    def from_result(
        cls,
        result: IngestPaperResult,
    ) -> "IngestPaperResponse":
        """Create an API response from an application result."""

        paper = result.paper

        return cls(
            id=paper.id,
            doi=paper.doi,
            normalized_doi=paper.normalized_doi,
            title=paper.title,
            normalized_title=paper.normalized_title,
            abstract=paper.abstract,
            journal=paper.journal,
            publication_date=paper.publication_date,
            source_url=(
                HttpUrl(paper.source_url) if paper.source_url is not None else None
            ),
            ingestion_source=paper.ingestion_source,
            provider_record_id=paper.provider_record_id,
            created_at=paper.created_at,
            updated_at=paper.updated_at,
            created=result.created,
        )
