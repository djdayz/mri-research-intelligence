from collections.abc import Callable
from datetime import date
from time import sleep as default_sleep
from typing import Protocol

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from mrinsight.discovery.records import (
    DiscoveryCandidate,
    DiscoverySearchRequest,
    DiscoverySearchResult,
)
from mrinsight.papers import normalize_doi


class DiscoveryProviderError(RuntimeError):
    """Base error for discovery providers."""


class DiscoveryProviderUnavailableError(DiscoveryProviderError):
    """Raised when a discovery provider cannot be reached."""


class InvalidDiscoveryProviderResponseError(DiscoveryProviderError):
    """Raised when a discovery provider returns invalid metadata."""


class DiscoveryProvider(Protocol):
    """Provider contract for topic/date-window discovery."""

    @property
    def name(self) -> str:
        """Return provider name."""

    def search(
        self,
        request: DiscoverySearchRequest,
    ) -> DiscoverySearchResult:
        """Search for candidate papers."""


class FakeDiscoveryProvider:
    """Deterministic discovery provider for offline tests."""

    def __init__(
        self,
        candidates: tuple[DiscoveryCandidate, ...],
        *,
        name: str = "fake-discovery",
    ) -> None:
        self._candidates = candidates
        self._name = name
        self.requests: list[DiscoverySearchRequest] = []

    @property
    def name(self) -> str:
        """Return provider name."""

        return self._name

    def search(
        self,
        request: DiscoverySearchRequest,
    ) -> DiscoverySearchResult:
        """Return deterministic candidate window."""

        self.requests.append(request)
        window = self._candidates[request.offset : request.offset + request.rows]

        return DiscoverySearchResult(
            candidates=window,
            provider_name=self.name,
            query=request.topic_query,
            rows=request.rows,
            offset=request.offset,
        )


class _CrossrefDiscoveryDateParts(BaseModel):
    """Date representation returned inside Crossref work metadata."""

    model_config = ConfigDict(extra="ignore")

    date_parts: list[list[int]] = Field(alias="date-parts")


class _CrossrefDiscoveryAuthor(BaseModel):
    """Author fields used by discovery."""

    model_config = ConfigDict(extra="ignore")

    given: str | None = None
    family: str | None = None
    name: str | None = None


class _CrossrefDiscoveryWork(BaseModel):
    """Subset of Crossref work metadata used by discovery."""

    model_config = ConfigDict(extra="ignore")

    doi: str | None = Field(default=None, alias="DOI")
    title: list[str] = Field(default_factory=list)
    abstract: str | None = None
    container_title: list[str] = Field(default_factory=list, alias="container-title")
    published_print: _CrossrefDiscoveryDateParts | None = Field(
        default=None,
        alias="published-print",
    )
    published_online: _CrossrefDiscoveryDateParts | None = Field(
        default=None,
        alias="published-online",
    )
    published: _CrossrefDiscoveryDateParts | None = None
    issued: _CrossrefDiscoveryDateParts | None = None
    url: str | None = Field(default=None, alias="URL")
    authors: list[_CrossrefDiscoveryAuthor] = Field(
        default_factory=list,
        alias="author",
    )
    score: float | None = None


class _CrossrefDiscoveryMessage(BaseModel):
    """Crossref works-list message."""

    model_config = ConfigDict(extra="ignore")

    items: list[_CrossrefDiscoveryWork] = Field(default_factory=list)


class _CrossrefDiscoveryEnvelope(BaseModel):
    """Crossref works-list response envelope."""

    model_config = ConfigDict(extra="ignore")

    status: str
    message: _CrossrefDiscoveryMessage


class CrossrefDiscoveryProvider:
    """Search candidates through Crossref's works endpoint."""

    def __init__(
        self,
        *,
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
        """Return provider name."""

        return "crossref-discovery"

    def search(
        self,
        request: DiscoverySearchRequest,
    ) -> DiscoverySearchResult:
        """Search Crossref works by query and publication date window."""

        response = self._get_with_retry(request)

        if response.status_code >= 400:
            raise DiscoveryProviderError(
                f"Crossref discovery failed with HTTP status {response.status_code}."
            )

        try:
            envelope = _CrossrefDiscoveryEnvelope.model_validate(response.json())
        except (ValueError, ValidationError) as error:
            raise InvalidDiscoveryProviderResponseError(
                "Crossref returned malformed discovery metadata."
            ) from error

        if envelope.status != "ok":
            raise InvalidDiscoveryProviderResponseError(
                "Crossref returned an unexpected discovery envelope."
            )

        return DiscoverySearchResult(
            candidates=tuple(
                candidate
                for work in envelope.message.items
                if (candidate := _to_discovery_candidate(work, self.name)) is not None
            ),
            provider_name=self.name,
            query=request.topic_query,
            rows=request.rows,
            offset=request.offset,
        )

    def _get_with_retry(
        self,
        request: DiscoverySearchRequest,
    ) -> httpx.Response:
        """Execute a bounded works search with retry."""

        filters = ",".join(
            (
                f"from-pub-date:{request.from_publication_date.isoformat()}",
                f"until-pub-date:{request.until_publication_date.isoformat()}",
                "type:journal-article",
            )
        )
        url = f"{self._base_url}/works"

        for attempt in range(self._max_attempts):
            try:
                response = self._client.get(
                    url,
                    params={
                        "query.bibliographic": request.topic_query,
                        "filter": filters,
                        "rows": request.rows,
                        "offset": request.offset,
                        "mailto": self._mailto,
                    },
                    headers={
                        "Accept": "application/json",
                        "User-Agent": f"{self._user_agent} (mailto:{self._mailto})",
                    },
                )
            except httpx.TransportError as error:
                if attempt == self._max_attempts - 1:
                    raise DiscoveryProviderUnavailableError(
                        "Crossref discovery could not be reached."
                    ) from error
                self._sleep_before_retry(attempt)
                continue

            if response.status_code in {408, 429, 500, 502, 503, 504}:
                if attempt == self._max_attempts - 1:
                    raise DiscoveryProviderUnavailableError(
                        "Crossref discovery remained unavailable after retry."
                    )
                self._sleep_before_retry(attempt)
                continue

            return response

        raise RuntimeError("Crossref discovery retry loop ended unexpectedly.")

    def _sleep_before_retry(
        self,
        attempt: int,
    ) -> None:
        """Wait before retrying."""

        delay = self._backoff_seconds * (2**attempt)
        if delay > 0:
            self._sleeper(delay)


def _to_discovery_candidate(
    work: _CrossrefDiscoveryWork,
    provider_name: str,
) -> DiscoveryCandidate | None:
    """Translate Crossref work metadata into a discovery candidate."""

    title = _first_nonempty(work.title)
    if title is None:
        return None

    doi = None
    provider_record_id = None
    if work.doi is not None:
        try:
            doi = normalize_doi(work.doi)
            provider_record_id = doi
        except ValueError:
            doi = None

    return DiscoveryCandidate(
        title=title,
        doi=doi,
        abstract=_clean_optional_text(work.abstract),
        journal=_first_nonempty(work.container_title),
        publication_date=_extract_complete_date(work),
        source_url=_clean_optional_text(work.url),
        authors=tuple(
            author_name
            for author in work.authors
            if (author_name := _format_author_name(author)) is not None
        ),
        provider_name=provider_name,
        provider_record_id=provider_record_id,
        raw_score=work.score,
    )


def _first_nonempty(
    values: list[str],
) -> str | None:
    """Return first non-empty string."""

    for value in values:
        cleaned = value.strip()
        if cleaned:
            return cleaned
    return None


def _clean_optional_text(
    value: str | None,
) -> str | None:
    """Strip optional text."""

    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _format_author_name(
    author: _CrossrefDiscoveryAuthor,
) -> str | None:
    """Construct author name from available fields."""

    parts = [
        part.strip()
        for part in (author.given, author.family)
        if part is not None and part.strip()
    ]
    if parts:
        return " ".join(parts)
    return _clean_optional_text(author.name)


def _extract_complete_date(
    work: _CrossrefDiscoveryWork,
) -> date | None:
    """Return a complete publication date without inventing precision."""

    for candidate in (
        work.published_print,
        work.published_online,
        work.published,
        work.issued,
    ):
        if candidate is None or not candidate.date_parts:
            continue
        parts = candidate.date_parts[0]
        if len(parts) >= 3:
            try:
                return date(parts[0], parts[1], parts[2])
            except ValueError:
                continue
    return None
