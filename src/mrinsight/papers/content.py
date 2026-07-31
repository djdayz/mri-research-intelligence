from enum import StrEnum


class ContentType(StrEnum):
    """Scientific-document content available for analysis."""

    ABSTRACT = "abstract"
    FULL_TEXT = "full_text"


class ExtractionStatus(StrEnum):
    """Outcome of a scientific-text extraction attempt."""

    SUCCEEDED = "succeeded"
    FAILED = "failed"


class SectionType(StrEnum):
    """Canonical scientific-document section labels."""

    ABSTRACT = "abstract"
    BACKGROUND = "background"
    INTRODUCTION = "introduction"
    METHODS = "methods"
    RESULTS = "results"
    DISCUSSION = "discussion"
    LIMITATIONS = "limitations"
    CONCLUSION = "conclusion"
    REFERENCES = "references"
    OTHER = "other"
