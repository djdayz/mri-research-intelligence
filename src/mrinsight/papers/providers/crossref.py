from collections.abc import Callable
from datetime import date
from time import sleep as default_sleep
from typing import Final
from urllib.parse import quote

import httpx
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, ValidationError

from mrinsight.papers.doi import normalize_doi
from mrinsight.papers.metadata import ResolvedPaperMetadata
from mrinsight.papers.providers.base import (
    BibliographicProviderError,
    BibliographicProviderUnavailableError,
    BibliographicRecordNotFoundError,
    InvalidBibliographicResponseError,
)

RETRYABLE_STATUS_CODES: Final[frozenset[int]] = frozenset(
    {
        408,
        429,
        500,
        502,
        503,
        504,
    }
)


class _CrossrefDateParts(BaseModel):
    """Date representation returned inside Crossref work metadata."""

    model_config = ConfigDict(extra="ignore")

    date_parts: list[list[int]] = Field(alias="date-parts")


class _CrossrefAuthor(BaseModel):
    """Author fields used by MRInsight."""

    model_config = ConfigDict(extra="ignore")

    given: str | None = None
    family: str | None = None
    name: str | None = None


class _CrossrefWork(BaseModel):
    """Subset of a Crossref work record used by MRInsight."""

    model_config = ConfigDict(extra="ignore")

    doi: str = Field(alias="DOI")
    title: list[str] = Field(default_factory=list)
    abstract: str | None = None

    container_title: list[str] = Field(
        default_factory=list,
        alias="container-title",
    )

    published_print: _CrossrefDateParts | None = Field(
        default=None,
        alias="published-print",
    )

    published_online: _CrossrefDateParts | None = Field(
        default=None,
        alias="published-online",
    )

    published: _CrossrefDateParts | None = None
    issued: _CrossrefDateParts | None = None

    url: str | None = Field(
        default=None,
        alias="URL",
    )

    authors: list[_CrossrefAuthor] = Field(
        default_factory=list,
        alias="author",
    )


class _CrossrefEnvelope(BaseModel):
    """Top-level response returned for a singleton Crossref work."""

    model_config = ConfigDict(extra="ignore")

    status: str
    message_type: str = Field(alias="message-type")
    message: _CrossrefWork


class CrossrefBibliographicProvider:
    """Resolve DOI metadata through the Crossref REST API."""

    def __init__(
        self,
        client: httpx.Client,
        mailto: str,
        user_agent: str,
        base_url: str = "https://api.crossref.org",
        max_attempts: int = 3,
        backoff_seconds: float = 0.5,
        sleeper: Callable[[float], None] = default_sleep,
    ) -> None:
        if not mailto.strip():
            raise ValueError("Crossref contact email cannot be empty.")

        if not user_agent.strip():
            raise ValueError("Crossref user agent cannot be empty.")

        if max_attempts < 1:
            raise ValueError("max_attempts must be at least 1.")

        if backoff_seconds < 0:
            raise ValueError("backoff_seconds cannot be negative.")

        self._client = client
        self._mailto = mailto.strip()
        self._user_agent = user_agent.strip()
        self._base_url = base_url.rstrip("/")
        self._max_attempts = max_attempts
        self._backoff_seconds = backoff_seconds
        self._sleeper = sleeper

    @property
    def name(self) -> str:
        """Return the provider's stable application name."""

        return "crossref"

    def resolve_by_doi(
        self,
        doi: str,
    ) -> ResolvedPaperMetadata:
        """Resolve a DOI into validated bibliographic metadata."""

        normalized_doi = normalize_doi(doi)
        encoded_doi = quote(normalized_doi, safe="/")

        response = self._get_with_retry(encoded_doi)

        if response.status_code == httpx.codes.NOT_FOUND:
            raise BibliographicRecordNotFoundError(
                f"Crossref contains no work record for DOI {normalized_doi!r}."
            )

        if response.status_code == httpx.codes.FORBIDDEN:
            raise BibliographicProviderUnavailableError(
                "Crossref rejected or blocked the request."
            )

        if response.status_code >= 400:
            raise BibliographicProviderError(
                f"Crossref request failed with HTTP status {response.status_code}."
            )

        try:
            envelope = _CrossrefEnvelope.model_validate(response.json())
        except (ValueError, ValidationError) as error:
            raise InvalidBibliographicResponseError(
                "Crossref returned malformed JSON metadata."
            ) from error

        if envelope.status != "ok" or envelope.message_type != "work":
            raise InvalidBibliographicResponseError(
                "Crossref returned an unexpected response envelope."
            )

        return self._to_metadata(envelope.message)

    def _get_with_retry(
        self,
        encoded_doi: str,
    ) -> httpx.Response:
        """Execute a bounded request with exponential backoff."""

        url = f"{self._base_url}/works/{encoded_doi}"

        for attempt in range(self._max_attempts):
            try:
                response = self._client.get(
                    url,
                    params={"mailto": self._mailto},
                    headers={
                        "Accept": "application/json",
                        "User-Agent": (f"{self._user_agent} (mailto:{self._mailto})"),
                    },
                )
            except httpx.TransportError as error:
                if attempt == self._max_attempts - 1:
                    raise BibliographicProviderUnavailableError(
                        "Crossref could not be reached."
                    ) from error

                self._sleep_before_retry(attempt)
                continue

            if response.status_code in RETRYABLE_STATUS_CODES:
                if attempt == self._max_attempts - 1:
                    raise BibliographicProviderUnavailableError(
                        "Crossref remained unavailable after "
                        f"{self._max_attempts} attempts."
                    )

                self._sleep_before_retry(attempt)
                continue

            return response

        raise RuntimeError("Crossref retry loop ended unexpectedly.")

    def _sleep_before_retry(
        self,
        attempt: int,
    ) -> None:
        """Wait before retrying a transient provider failure."""

        delay = self._backoff_seconds * (2**attempt)

        if delay > 0:
            self._sleeper(delay)

    def _to_metadata(
        self,
        work: _CrossrefWork,
    ) -> ResolvedPaperMetadata:
        """Translate Crossref fields into MRInsight metadata."""

        title = _first_nonempty(work.title)

        if title is None:
            raise InvalidBibliographicResponseError(
                "Crossref work metadata does not contain a title."
            )

        journal = _first_nonempty(work.container_title)
        abstract = _clean_optional_text(work.abstract)
        source_url = _clean_optional_text(work.url)

        authors = tuple(
            author_name
            for author in work.authors
            if (author_name := _format_author_name(author)) is not None
        )

        publication_date = _extract_complete_date(work)

        try:
            return ResolvedPaperMetadata(
                doi=work.doi,
                title=title,
                abstract=abstract,
                journal=journal,
                publication_date=publication_date,
                source_url=HttpUrl(source_url) if source_url is not None else None,
                authors=authors,
                provider_name=self.name,
                provider_record_id=normalize_doi(work.doi),
            )
        except ValidationError as error:
            raise InvalidBibliographicResponseError(
                "Crossref work metadata failed MRInsight validation."
            ) from error


def _first_nonempty(
    values: list[str],
) -> str | None:
    """Return the first non-empty text value."""

    for value in values:
        cleaned = value.strip()

        if cleaned:
            return cleaned

    return None


def _clean_optional_text(
    value: str | None,
) -> str | None:
    """Strip optional provider text without inventing content."""

    if value is None:
        return None

    cleaned = value.strip()

    return cleaned or None


def _format_author_name(
    author: _CrossrefAuthor,
) -> str | None:
    """Construct an author name from available Crossref fields."""

    name_parts = [
        part.strip()
        for part in (author.given, author.family)
        if part is not None and part.strip()
    ]

    if name_parts:
        return " ".join(name_parts)

    return _clean_optional_text(author.name)


def _extract_complete_date(
    work: _CrossrefWork,
) -> date | None:
    """Return a complete publication date without inventing precision."""

    candidates = (
        work.published_print,
        work.published_online,
        work.published,
        work.issued,
    )

    for candidate in candidates:
        if candidate is None or not candidate.date_parts:
            continue

        parts = candidate.date_parts[0]

        if len(parts) < 3:
            continue

        year = parts[0]
        month = parts[1]
        day = parts[2]

        try:
            return date(year, month, day)
        except ValueError as error:
            raise InvalidBibliographicResponseError(
                "Crossref returned an invalid publication date."
            ) from error

    return None
