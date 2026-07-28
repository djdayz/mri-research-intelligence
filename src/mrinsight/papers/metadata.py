from datetime import date

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    field_validator,
)

from mrinsight.papers.doi import normalize_doi
from mrinsight.papers.title import normalize_title


class ResolvedPaperMetadata(BaseModel):
    """Validated bibliographic metadata returned by a trusted provider"""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        str_strip_whitespace=True,
    )

    doi: str
    title: str = Field(min_length=1)
    abstract: str | None = None
    journal: str | None = None
    publication_date: date | None = None
    source_url: HttpUrl | None = None
    authors: tuple[str, ...] = ()
    provider_name: str = Field(min_length=1)
    provider_record_id: str | None = None

    @field_validator("doi")
    @classmethod
    def normalize_verified_doi(cls, value: str) -> str:
        """Store provider DOI values in canonical form"""

        return normalize_doi(value)

    @field_validator("title")
    @classmethod
    def validate_title_content(cls, value: str) -> str:
        """Reject titles that contain no meaningful characters"""

        normalize_title(value)
        return value

    @field_validator("authors")
    @classmethod
    def clean_author_names(
        cls,
        authors: tuple[str, ...],
    ) -> tuple[str, ...]:
        """Strip author names and reject empty entries"""

        cleaned_authors = tuple(author.strip() for author in authors)

        if any(not author for author in cleaned_authors):
            raise ValueError("Author names cannot be empty.")

        return cleaned_authors
