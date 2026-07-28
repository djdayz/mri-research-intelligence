from collections.abc import Iterable

from mrinsight.papers.doi import normalize_doi
from mrinsight.papers.metadata import ResolvedPaperMetadata
from mrinsight.papers.providers.base import (
    BibliographicRecordNotFoundError,
)


class FakeBibliographicProvider:
    """Resolve metadata from a deterministic in-memory catalogue"""

    def __init__(
        self,
        records: Iterable[ResolvedPaperMetadata],
    ) -> None:
        self._records_by_doi: dict[
            str,
            ResolvedPaperMetadata,
        ] = {}

        for record in records:
            if record.doi in self._records_by_doi:
                raise ValueError(
                    f"Duplicate DOI in fake provider catalogue: {record.doi}"
                )

            self._records_by_doi[record.doi] = record

    @property
    def name(self) -> str:
        """Return the provider's stable application name"""

        return "fake"

    def resolve_by_doi(
        self,
        doi: str,
    ) -> ResolvedPaperMetadata:
        """Return the matching record or raise a NotFound error"""

        normalized_doi = normalize_doi(doi)

        try:
            return self._records_by_doi[normalized_doi]
        except KeyError as error:
            raise BibliographicRecordNotFoundError(
                f"No bibliographic record found for DOI {normalized_doi!r}."
            ) from error
