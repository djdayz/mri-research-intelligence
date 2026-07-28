from typing import Protocol

from mrinsight.papers.metadata import ResolvedPaperMetadata


class BibliographicProviderError(RuntimeError):
    """Base error for bibliographic-provider failures"""


class BibliographicRecordNotFoundError(BibliographicProviderError):
    """Raised when no provider record exists for an identifier"""


class BibliographicProviderUnavailableError(BibliographicProviderError):
    """Raised when a provider cannot be reached temporarily"""


class InvalidBibliographicResponseError(BibliographicProviderError):
    """Raised when provider data cannot be validated"""


class BibliographicProvider(Protocol):
    """Contract implemented by bibliographic metadata providers"""

    @property
    def name(self) -> str:
        """Return the provider's stable application name"""

        ...

    def resolve_by_doi(
        self,
        doi: str,
    ) -> ResolvedPaperMetadata:
        """Resolve a DOI into validated bibliographic metadata"""

        ...
