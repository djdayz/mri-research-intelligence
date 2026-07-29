from mrinsight.papers.metadata import ResolvedPaperMetadata
from mrinsight.papers.providers.base import (
    BibliographicProviderUnavailableError,
)


class UnconfiguredBibliographicProvider:
    """Provider used until a real adapter is configured."""

    @property
    def name(self) -> str:
        """Return the provider's stable application name."""

        return "unconfigured"

    def resolve_by_doi(
        self,
        doi: str,
    ) -> ResolvedPaperMetadata:
        """Raise because no real provider is configured."""

        raise BibliographicProviderUnavailableError(
            "No bibliographic provider has been configured."
        )
