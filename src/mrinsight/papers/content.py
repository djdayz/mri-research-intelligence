from enum import StrEnum


class ContentType(StrEnum):
    """Scientific-document content available for analysis."""

    ABSTRACT = "abstract"
    FULL_TEXT = "full_text"


class ExtractionStatus(StrEnum):
    """Outcome of a scientific-text extraction attempt."""

    SUCCEEDED = "succeeded"
    FAILED = "failed"
