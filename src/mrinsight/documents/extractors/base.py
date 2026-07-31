from typing import Protocol

from mrinsight.documents.pdf import (
    ExtractedPdfDocument,
    PdfInspection,
    ValidatedPdfUpload,
)


class PdfDocumentInspector(Protocol):
    """Contract for safely inspecting PDF bytes."""

    @property
    def name(self) -> str:
        """Return the adapter's stable name."""

        ...

    def inspect(
        self,
        data: bytes,
    ) -> PdfInspection:
        """Parse document-level information from PDF bytes."""

        ...


class PdfTextExtractor(Protocol):
    """Contract for extracting deterministic PDF text."""

    @property
    def name(self) -> str:
        """Return the adapter's stable name."""

        ...

    @property
    def version(self) -> str:
        """Return the extraction-algorithm version."""

        ...

    def extract(
        self,
        document: ValidatedPdfUpload,
    ) -> ExtractedPdfDocument:
        """Extract page-aware text from a validated PDF."""

        ...
