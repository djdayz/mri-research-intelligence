import pytest
from pydantic import ValidationError

from mrinsight.analysis import (
    EvidenceBackedText,
    EvidenceReference,
    EvidenceRole,
    InformationStatus,
)
from mrinsight.papers import SectionType


def make_reference() -> EvidenceReference:
    """Create a valid evidence reference."""

    return EvidenceReference(
        paper_id=1,
        content_id=2,
        chunk_id=3,
        section=SectionType.METHODS,
        start_page=1,
        end_page=1,
        start_char=10,
        end_char=30,
        excerpt="MRI methods",
        role=EvidenceRole.PRIMARY,
    )


def test_reported_statement_requires_evidence() -> None:
    with pytest.raises(ValidationError):
        EvidenceBackedText(
            status=InformationStatus.REPORTED,
            text="This is a reported claim.",
            evidence_references=(),
        )


def test_reference_requires_matching_page_pair() -> None:
    with pytest.raises(ValidationError):
        EvidenceReference(
            paper_id=1,
            content_id=2,
            chunk_id=3,
            section=SectionType.METHODS,
            start_page=1,
            end_page=None,
            start_char=10,
            end_char=30,
            role=EvidenceRole.PRIMARY,
        )


def test_schema_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError):
        EvidenceReference.model_validate(
            {
                "paper_id": 1,
                "content_id": 2,
                "chunk_id": 3,
                "section": "methods",
                "start_char": 10,
                "end_char": 30,
                "role": "primary",
                "surprise": "nope",
            }
        )


def test_reported_statement_accepts_evidence() -> None:
    statement = EvidenceBackedText(
        status=InformationStatus.REPORTED,
        text="This is a reported claim.",
        evidence_references=(make_reference(),),
    )

    assert statement.evidence_references[0].chunk_id == 3
