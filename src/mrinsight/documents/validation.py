import hashlib
from pathlib import PurePath
from typing import Final

from mrinsight.documents.extractors.base import (
    PdfDocumentInspector,
)
from mrinsight.documents.pdf import (
    InvalidPdfUploadError,
    PdfFileTooLargeError,
    PdfPageLimitError,
    PdfUploadCandidate,
    PdfUploadPolicy,
    UnsupportedPdfMediaTypeError,
    ValidatedPdfUpload,
)

PDF_HEADER_MARKER: Final[bytes] = b"%PDF-"
PDF_HEADER_SEARCH_BYTES: Final[int] = 1024


def validate_pdf_upload(
    candidate: PdfUploadCandidate,
    *,
    inspector: PdfDocumentInspector,
    policy: PdfUploadPolicy | None = None,
) -> ValidatedPdfUpload:
    """Validate one PDF upload without extracting page text."""

    effective_policy = policy or PdfUploadPolicy()

    filename = _safe_filename(candidate.filename)
    _validate_filename(filename)

    content_type = _normalize_content_type(candidate.content_type)

    if content_type not in effective_policy.accepted_media_types:
        raise UnsupportedPdfMediaTypeError(
            f"Unsupported PDF media type: {content_type!r}."
        )

    if not isinstance(candidate.data, bytes):
        raise InvalidPdfUploadError("PDF upload data must be bytes.")

    byte_size = len(candidate.data)

    if byte_size == 0:
        raise InvalidPdfUploadError("PDF upload cannot be empty.")

    if byte_size > effective_policy.max_bytes:
        raise PdfFileTooLargeError("PDF upload exceeds the configured size limit.")

    header_region = candidate.data[:PDF_HEADER_SEARCH_BYTES]

    if PDF_HEADER_MARKER not in header_region:
        raise InvalidPdfUploadError("Uploaded data does not contain a PDF header.")

    inspection = inspector.inspect(candidate.data)

    if inspection.page_count < 1:
        raise InvalidPdfUploadError("PDF document must contain at least one page.")

    if inspection.page_count > effective_policy.max_pages:
        raise PdfPageLimitError("PDF document exceeds the configured page limit.")

    checksum = hashlib.sha256(candidate.data).hexdigest()

    return ValidatedPdfUpload(
        filename=filename,
        content_type=content_type,
        data=candidate.data,
        byte_size=byte_size,
        sha256=checksum,
        page_count=inspection.page_count,
        pdf_header=inspection.pdf_header,
        access_basis=candidate.access_basis,
    )


def _safe_filename(value: str) -> str:
    """Remove any client-supplied path components."""

    filename = PurePath(value.strip()).name

    if not filename:
        raise InvalidPdfUploadError("PDF filename cannot be empty.")

    return filename


def _validate_filename(filename: str) -> None:
    """Require a conventional PDF filename extension."""

    if PurePath(filename).suffix.casefold() != ".pdf":
        raise InvalidPdfUploadError("Uploaded filename must end with .pdf.")


def _normalize_content_type(
    value: str | None,
) -> str:
    """Return a canonical media type without parameters."""

    if value is None:
        raise UnsupportedPdfMediaTypeError("A PDF media type is required.")

    media_type = value.split(";", maxsplit=1)[0]
    media_type = media_type.strip().casefold()

    if not media_type:
        raise UnsupportedPdfMediaTypeError("A PDF media type is required.")

    return media_type
