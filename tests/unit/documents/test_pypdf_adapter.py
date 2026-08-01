from io import BytesIO

import pytest
from pypdf import PdfWriter
from tests.helpers.pdf_factory import build_blank_pdf, build_text_pdf

from mrinsight.documents import (
    DocumentAccessBasis,
    EncryptedPdfError,
    MalformedPdfError,
    PdfTextUnavailableError,
    PdfUploadCandidate,
    validate_pdf_upload,
)
from mrinsight.documents.extractors import (
    PYPDF_EXTRACTOR_VERSION,
    PypdfDocumentAdapter,
)


def make_candidate(
    data: bytes,
) -> PdfUploadCandidate:
    """Create an upload candidate for adapter tests."""

    return PdfUploadCandidate(
        filename="paper.pdf",
        content_type="application/pdf",
        data=data,
        access_basis=DocumentAccessBasis.USER_UPLOAD,
    )


def build_encrypted_pdf() -> bytes:
    """Build a password-protected test PDF."""

    output = BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(
        width=612,
        height=792,
    )
    writer.encrypt("test-password")
    writer.write(output)

    return output.getvalue()


def test_pypdf_adapter_inspects_pdf() -> None:
    data = build_text_pdf(
        [
            ["First page"],
            ["Second page"],
        ]
    )
    adapter = PypdfDocumentAdapter()

    inspection = adapter.inspect(data)

    assert inspection.page_count == 2
    assert inspection.pdf_header.startswith("%PDF-")


def test_pypdf_adapter_extracts_page_aware_text() -> None:
    data = build_text_pdf(
        [
            [
                "Methods",
                "MRI data were acquired at 3 T.",
            ],
            [
                "Results",
                "RMSE decreased to 0.20.",
            ],
        ]
    )
    adapter = PypdfDocumentAdapter()

    validated = validate_pdf_upload(
        make_candidate(data),
        inspector=adapter,
    )
    extracted = adapter.extract(validated)

    assert extracted.page_count == 2
    assert extracted.text_page_count == 2
    assert extracted.extractor_name == "pypdf"
    assert extracted.extractor_version == (PYPDF_EXTRACTOR_VERSION)
    assert extracted.source_sha256 == validated.sha256

    assert [page.page_number for page in extracted.pages] == [1, 2]

    first_page = extracted.pages[0]
    second_page = extracted.pages[1]

    assert (
        extracted.text[first_page.start_char : first_page.end_char] == first_page.text
    )

    assert (
        extracted.text[second_page.start_char : second_page.end_char]
        == second_page.text
    )

    assert "Methods" in first_page.text
    assert "MRI data were acquired at 3 T." in (first_page.text)
    assert "Results" in second_page.text
    assert "RMSE decreased to 0.20." in (second_page.text)


def test_pypdf_adapter_rejects_encrypted_pdf() -> None:
    adapter = PypdfDocumentAdapter()

    with pytest.raises(
        EncryptedPdfError,
        match="Encrypted PDFs are not supported",
    ):
        adapter.inspect(build_encrypted_pdf())


def test_pypdf_adapter_rejects_malformed_pdf() -> None:
    adapter = PypdfDocumentAdapter()

    with pytest.raises(MalformedPdfError):
        adapter.inspect(b"%PDF-1.7\nthis is not a valid PDF")


def test_pypdf_adapter_reports_textless_pdf() -> None:
    adapter = PypdfDocumentAdapter()
    data = build_blank_pdf()

    validated = validate_pdf_upload(
        make_candidate(data),
        inspector=adapter,
    )

    with pytest.raises(
        PdfTextUnavailableError,
        match="no extractable text",
    ):
        adapter.extract(validated)
