from dataclasses import dataclass

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


class IngestPaperService:
    """Resolve and persist one paper by DOI."""

    def __init__(
        self,
        provider: BibliographicProvider,
        repository: PaperRepository,
    ) -> None:
        self._provider = provider
        self._repository = repository

    def execute(
        self,
        doi: str,
    ) -> IngestPaperResult:
        """Resolve and persist a DOI without creating duplicates."""

        requested_doi = normalize_doi(doi)

        existing = self._repository.get_by_normalized_doi(requested_doi)

        if existing is not None:
            return IngestPaperResult(
                paper=existing,
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
            return IngestPaperResult(
                paper=existing,
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

        return IngestPaperResult(
            paper=stored_paper,
            created=True,
        )
