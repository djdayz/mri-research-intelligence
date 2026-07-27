from datetime import date

import pytest
from pydantic import HttpUrl, ValidationError

from mrinsight.papers import ResolvedPaperMetadata


def test_resolved_metadata_normalizes_and_preserves_fields() -> None:
    record = ResolvedPaperMetadata(
        doi="https://doi.org/10.1234/MRI.EXAMPLE",
        title="  Deep Learning for MRI Reconstruction  ",
        abstract="An MRI reconstruction study.",
        journal="Journal of MRI Research",
        publication_date=date(2026, 3, 15),
        source_url=HttpUrl("https://example.org/papers/mri-example"),
        authors=(
            " Alice Smith ",
            "Bob Jones",
        ),
        provider_name="fake",
        provider_record_id="record-001",
    )

    assert record.doi == "10.1234/mri.example"
    assert record.title == "Deep Learning for MRI Reconstruction"
    assert record.authors == (
        "Alice Smith",
        "Bob Jones",
    )
    assert record.publication_date == date(2026, 3, 15)


def test_resolved_metadata_rejects_invalid_doi() -> None:
    with pytest.raises(ValidationError):
        ResolvedPaperMetadata(
            doi="not-a-doi",
            title="An MRI Paper",
            provider_name="fake",
        )


def test_resolved_metadata_rejects_empty_title() -> None:
    with pytest.raises(ValidationError):
        ResolvedPaperMetadata(
            doi="10.1234/example",
            title="---",
            provider_name="fake",
        )


def test_resolved_metadata_rejects_empty_author_name() -> None:
    with pytest.raises(
        ValidationError,
        match="Author names cannot be empty",
    ):
        ResolvedPaperMetadata(
            doi="10.1234/example",
            title="An MRI Paper",
            authors=("Alice Smith", "  "),
            provider_name="fake",
        )


def test_resolved_metadata_rejects_unexpected_fields() -> None:
    with pytest.raises(ValidationError):
        ResolvedPaperMetadata(
            doi="10.1234/example",
            title="An MRI Paper",
            provider_name="fake",
            unexpected_field="unexpected",
        )  # type: ignore[call-arg]
