from dataclasses import dataclass
from enum import StrEnum
from typing import Final

MEBIBYTE: Final[int] = 1024 * 1024


class DocumentAccessBasis(StrEnum):
    """How MRInsight obtained access to a document."""

    USER_UPLOAD = "user_upload"
    OPEN_ACCESS = "open_access"


class PdfDocumentError(RuntimeError):
    """Base error for PDF validation and extraction."""


class InvalidPdfUploadError(PdfDocumentError):
    """Raised when uploaded data violates the PDF policy."""


class UnsupportedPdfMediaTypeError(InvalidPdfUploadError):
    """Raised when an upload is not labelled as a PDF."""


class PdfFileTooLargeError(InvalidPdfUploadError):
    """Raised when an uploaded PDF exceeds the byte limit."""


class MalformedPdfError(InvalidPdfUploadError):
    """Raised when uploaded data cannot be parsed as a PDF."""


class EncryptedPdfError(InvalidPdfUploadError):
    """Raised when a PDF requires encrypted-document handling."""


class PdfPageLimitError(InvalidPdfUploadError):
    """Raised when a PDF exceeds the configured page limit."""


class PdfTextExtractionError(PdfDocumentError):
    """Raised when text extraction fails unexpectedly."""


class PdfTextUnavailableError(PdfTextExtractionError):
    """Raised when a valid PDF contains no extractable text."""


@dataclass(frozen=True, slots=True)
class PdfUploadPolicy:
    """Limits applied before scientific-text extraction."""

    max_bytes: int = 25 * MEBIBYTE
    max_pages: int = 500
    accepted_media_types: frozenset[str] = frozenset(
        {
            "application/pdf",
            "application/x-pdf",
        }
    )

    def __post_init__(self) -> None:
        if self.max_bytes < 1:
            raise ValueError("max_bytes must be at least 1.")

        if self.max_pages < 1:
            raise ValueError("max_pages must be at least 1.")

        if not self.accepted_media_types:
            raise ValueError("At least one PDF media type is required.")


@dataclass(frozen=True, slots=True)
class PdfUploadCandidate:
    """Raw user-supplied PDF data awaiting validation."""

    filename: str
    content_type: str | None
    data: bytes
    access_basis: DocumentAccessBasis


@dataclass(frozen=True, slots=True)
class PdfInspection:
    """Document-level information obtained from a PDF parser."""

    page_count: int
    pdf_header: str


@dataclass(frozen=True, slots=True)
class ValidatedPdfUpload:
    """A PDF that passed the configured upload policy."""

    filename: str
    content_type: str
    data: bytes
    byte_size: int
    sha256: str
    page_count: int
    pdf_header: str
    access_basis: DocumentAccessBasis


@dataclass(frozen=True, slots=True)
class ExtractedPdfPage:
    """Extracted text and offsets for one text-bearing PDF page."""

    page_number: int
    text: str
    start_char: int
    end_char: int


@dataclass(frozen=True, slots=True)
class ExtractedPdfDocument:
    """Deterministic page-aware PDF text extraction result."""

    text: str
    pages: tuple[ExtractedPdfPage, ...]
    page_count: int
    text_page_count: int
    source_sha256: str
    extractor_name: str
    extractor_version: str
    library_version: str
