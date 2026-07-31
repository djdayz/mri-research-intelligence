from dataclasses import dataclass
from typing import Protocol

from mrinsight.application.services.build_paper_chunks import (
    BuildPaperChunksResult,
    BuildPaperChunksService,
)
from mrinsight.application.services.store_abstract_content import (
    StoreAbstractContentResult,
    StoreAbstractContentService,
)
from mrinsight.papers.doi import normalize_doi
from mrinsight.papers.providers import BibliographicProvider
from mrinsight.papers.records import NewPaper, StoredPaper
from mrinsight.papers.repositories import PaperRepository
from mrinsight.papers.title import normalize_title


class BibliographicIdentityMismatchError(RuntimeError):
    """Raised when a provider resolves a different DOI."""


@dataclass(frozen=True, slots=True)
class IngestPaperResult:
    """Result of an idempotent paper-ingestion operation."""

    paper: StoredPaper
    created: bool
    abstract_content: StoreAbstractContentResult
    chunk_build: BuildPaperChunksResult | None


class AbstractContentService(Protocol):
    """Application service that stores abstract evidence."""

    def execute(
        self,
        paper_id: int,
        abstract: str | None,
    ) -> StoreAbstractContentResult:
        """Store abstract evidence for one paper."""

        ...


class IngestPaperService:
    """Resolve and persist one paper by DOI."""

    def __init__(
        self,
        provider: BibliographicProvider,
        repository: PaperRepository,
        abstract_content_service: StoreAbstractContentService,
        chunk_service: BuildPaperChunksService,
    ) -> None:
        self._provider = provider
        self._repository = repository
        self._abstract_content_service = abstract_content_service
        self._chunk_service = chunk_service

    def execute(
        self,
        doi: str,
    ) -> IngestPaperResult:
        """Resolve and persist a DOI without creating duplicates."""

        requested_doi = normalize_doi(doi)

        existing = self._repository.get_by_normalized_doi(requested_doi)

        if existing is not None:
            return self._build_result(
                existing,
                created=False,
            )

        metadata = self._provider.resolve_by_doi(requested_doi)

        if metadata.doi != requested_doi:
            raise BibliographicIdentityMismatchError(
                "Bibliographic provider returned DOI "
                f"{metadata.doi!r} for requested DOI "
                f"{requested_doi!r}."
            )

        existing = self._repository.get_by_normalized_doi(metadata.doi)

        if existing is not None:
            return self._build_result(
                existing,
                created=False,
            )

        source_url = (
            str(metadata.source_url) if metadata.source_url is not None else None
        )

        new_paper = NewPaper(
            doi=metadata.doi,
            normalized_doi=metadata.doi,
            title=metadata.title,
            normalized_title=normalize_title(metadata.title),
            abstract=metadata.abstract,
            journal=metadata.journal,
            publication_date=metadata.publication_date,
            source_url=source_url,
            ingestion_source=self._provider.name,
            provider_record_id=metadata.provider_record_id,
        )

        stored_paper = self._repository.add(new_paper)

        return self._build_result(
            stored_paper,
            created=True,
        )

    def _build_result(
        self,
        paper: StoredPaper,
        *,
        created: bool,
    ) -> IngestPaperResult:
        """Attach abstract evidence and chunks to ingestion."""

        abstract_content = self._abstract_content_service.execute(
            paper.id,
            paper.abstract,
        )

        chunk_build: BuildPaperChunksResult | None = None

        if abstract_content.content is not None:
            chunk_build = self._chunk_service.execute(abstract_content.content)

        return IngestPaperResult(
            paper=paper,
            created=created,
            abstract_content=abstract_content,
            chunk_build=chunk_build,
        )
