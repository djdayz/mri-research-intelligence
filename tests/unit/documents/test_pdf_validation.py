import hashlib

import pytest
from tests.helpers.pdf_factory import build_text_pdf

from mrinsight.documents import (
    DocumentAccessBasis,
    InvalidPdfUploadError,
    PdfFileTooLargeError,
    PdfInspection,
    PdfPageLimitError,
    PdfUploadCandidate,
    PdfUploadPolicy,
    UnsupportedPdfMediaTypeError,
    validate_pdf_upload,
)


class FakePdfInspector:
    """Return deterministic inspection information."""

    def __init__(
        self,
        *,
        page_count: int = 1,
    ) -> None:
        self._page_count = page_count

    @property
    def name(self) -> str:
        return "fake"

    def inspect(
        self,
        data: bytes,
    ) -> PdfInspection:
        return PdfInspection(
            page_count=self._page_count,
            pdf_header="%PDF-1.7",
        )


def make_candidate(
    *,
    data: bytes | None = None,
    filename: str = "paper.pdf",
    content_type: str | None = "application/pdf",
) -> PdfUploadCandidate:
    """Create a valid upload candidate."""

    return PdfUploadCandidate(
        filename=filename,
        content_type=content_type,
        data=data if data is not None else build_text_pdf([["MRI paper"]]),
        access_basis=DocumentAccessBasis.USER_UPLOAD,
    )


def test_valid_pdf_upload_is_canonicalized() -> None:
    candidate = make_candidate(
        filename="../../MRI-Paper.PDF",
        content_type="application/pdf; charset=binary",
    )

    validated = validate_pdf_upload(
        candidate,
        inspector=FakePdfInspector(page_count=2),
    )

    assert validated.filename == "MRI-Paper.PDF"
    assert validated.content_type == "application/pdf"
    assert validated.page_count == 2
    assert validated.byte_size == len(candidate.data)
    assert validated.sha256 == hashlib.sha256(candidate.data).hexdigest()
    assert validated.access_basis is (DocumentAccessBasis.USER_UPLOAD)


def test_upload_rejects_non_pdf_extension() -> None:
    with pytest.raises(
        InvalidPdfUploadError,
        match="must end with .pdf",
    ):
        validate_pdf_upload(
            make_candidate(filename="paper.txt"),
            inspector=FakePdfInspector(),
        )


def test_upload_rejects_unsupported_media_type() -> None:
    with pytest.raises(
        UnsupportedPdfMediaTypeError,
        match="application/octet-stream",
    ):
        validate_pdf_upload(
            make_candidate(content_type="application/octet-stream"),
            inspector=FakePdfInspector(),
        )


def test_upload_rejects_empty_file() -> None:
    with pytest.raises(
        InvalidPdfUploadError,
        match="PDF upload cannot be empty",
    ):
        validate_pdf_upload(
            make_candidate(data=b""),
            inspector=FakePdfInspector(),
        )


def test_upload_rejects_missing_pdf_header() -> None:
    with pytest.raises(
        InvalidPdfUploadError,
        match="does not contain a PDF header",
    ):
        validate_pdf_upload(
            make_candidate(data=b"not a pdf"),
            inspector=FakePdfInspector(),
        )


def test_upload_rejects_file_over_size_limit() -> None:
    candidate = make_candidate()

    with pytest.raises(PdfFileTooLargeError):
        validate_pdf_upload(
            candidate,
            inspector=FakePdfInspector(),
            policy=PdfUploadPolicy(
                max_bytes=len(candidate.data) - 1,
                max_pages=500,
            ),
        )


def test_upload_rejects_document_over_page_limit() -> None:
    with pytest.raises(PdfPageLimitError):
        validate_pdf_upload(
            make_candidate(),
            inspector=FakePdfInspector(page_count=11),
            policy=PdfUploadPolicy(
                max_bytes=25 * 1024 * 1024,
                max_pages=10,
            ),
        )
