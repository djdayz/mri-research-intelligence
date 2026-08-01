from io import BytesIO
from typing import Final

import pypdf
from pypdf import PdfReader
from pypdf.errors import (
    FileNotDecryptedError,
    PdfReadError,
)

from mrinsight.documents.pdf import (
    EncryptedPdfError,
    ExtractedPdfDocument,
    ExtractedPdfPage,
    MalformedPdfError,
    PdfInspection,
    PdfTextExtractionError,
    PdfTextUnavailableError,
    ValidatedPdfUpload,
)
from mrinsight.nlp import (
    InvalidScientificTextError,
    clean_scientific_text,
)

PYPDF_EXTRACTOR_VERSION: Final[str] = "pypdf-layout-v1"


class PypdfDocumentAdapter:
    """Inspect and extract text from PDFs using pypdf."""

    @property
    def name(self) -> str:
        """Return the adapter's stable application name."""

        return "pypdf"

    @property
    def version(self) -> str:
        """Return the extraction-algorithm version."""

        return PYPDF_EXTRACTOR_VERSION

    @property
    def library_version(self) -> str:
        """Return the installed pypdf version."""

        return pypdf.__version__

    def inspect(
        self,
        data: bytes,
    ) -> PdfInspection:
        """Parse PDF header, encryption state, and page count."""

        reader = self._open_reader(data)

        try:
            if reader.is_encrypted:
                raise EncryptedPdfError("Encrypted PDFs are not supported.")

            try:
                page_count = len(reader.pages)
            except (
                FileNotDecryptedError,
                PdfReadError,
                ValueError,
            ) as error:
                raise MalformedPdfError("PDF pages could not be read.") from error

            return PdfInspection(
                page_count=page_count,
                pdf_header=reader.pdf_header,
            )
        finally:
            reader.close()

    def extract(
        self,
        document: ValidatedPdfUpload,
    ) -> ExtractedPdfDocument:
        """Extract and clean text from each readable PDF page."""

        inspection = self.inspect(document.data)

        if inspection.page_count != document.page_count:
            raise PdfTextExtractionError("PDF page count changed after validation.")

        reader = self._open_reader(document.data)

        try:
            if reader.is_encrypted:
                raise EncryptedPdfError("Encrypted PDFs are not supported.")

            extracted_pages: list[ExtractedPdfPage] = []
            combined_parts: list[str] = []
            current_offset = 0

            for page_index, page in enumerate(reader.pages):
                if "/Contents" not in page:
                    continue

                try:
                    raw_text = page.extract_text(
                        extraction_mode="layout",
                        layout_mode_space_vertically=False,
                    )
                except (
                    FileNotDecryptedError,
                    PdfReadError,
                    TypeError,
                    ValueError,
                ) as error:
                    raise PdfTextExtractionError(
                        f"PDF text extraction failed on page {page_index + 1}."
                    ) from error

                if raw_text is None:
                    continue

                try:
                    cleaned_text = clean_scientific_text(raw_text)
                except InvalidScientificTextError:
                    continue

                if combined_parts:
                    combined_parts.append("\n\n")
                    current_offset += 2

                start_char = current_offset
                combined_parts.append(cleaned_text)
                current_offset += len(cleaned_text)
                end_char = current_offset

                extracted_pages.append(
                    ExtractedPdfPage(
                        page_number=page_index + 1,
                        text=cleaned_text,
                        start_char=start_char,
                        end_char=end_char,
                    )
                )

            if not extracted_pages:
                raise PdfTextUnavailableError(
                    "PDF contains no extractable text. It may be scanned or image-only."
                )

            combined_text = "".join(combined_parts)

            return ExtractedPdfDocument(
                text=combined_text,
                pages=tuple(extracted_pages),
                page_count=document.page_count,
                text_page_count=len(extracted_pages),
                source_sha256=document.sha256,
                extractor_name=self.name,
                extractor_version=self.version,
                library_version=self.library_version,
            )
        finally:
            reader.close()

    @staticmethod
    def _open_reader(
        data: bytes,
    ) -> PdfReader:
        """Create a reader and translate parser failures."""

        try:
            return PdfReader(
                BytesIO(data),
                strict=False,
            )
        except (
            PdfReadError,
            TypeError,
            ValueError,
        ) as error:
            raise MalformedPdfError(
                "Uploaded data could not be parsed as PDF."
            ) from error
