from mrinsight.papers.doi import InvalidDOIError, normalize_doi
from mrinsight.papers.metadata import ResolvedPaperMetadata
from mrinsight.papers.providers.base import (
    BibliographicProvider,
    BibliographicProviderError,
    BibliographicProviderUnavailableError,
    BibliographicRecordNotFoundError,
    InvalidBibliographicResponseError,
)
from mrinsight.papers.providers.fake import (
    FakeBibliographicProvider,
)
from mrinsight.papers.records import NewPaper, StoredPaper
from mrinsight.papers.title import (
    InvalidTitleError,
    build_title_year_fingerprint,
    normalize_title,
)

__all__ = [
    "BibliographicProvider",
    "BibliographicProviderError",
    "BibliographicProviderUnavailableError",
    "BibliographicRecordNotFoundError",
    "FakeBibliographicProvider",
    "InvalidDOIError",
    "InvalidBibliographicResponseError",
    "InvalidTitleError",
    "NewPaper",
    "ResolvedPaperMetadata",
    "StoredPaper",
    "build_title_year_fingerprint",
    "normalize_doi",
    "normalize_title",
]
