from datetime import date

import pytest
from pydantic import HttpUrl

from mrinsight.papers import ResolvedPaperMetadata
from mrinsight.papers.providers import (
    BibliographicProvider,
    BibliographicRecordNotFoundError,
    FakeBibliographicProvider,
)


def make_metadata_record(
    doi: str = "10.1234/mri.example",
) -> ResolvedPaperMetadata:
    """Create a small valid metadata record for provider tests"""

    return ResolvedPaperMetadata(
        doi=doi,
        title="Deep Learning for MRI Reconstruction",
        abstract="An MRI reconstruction study.",
        journal="Journal of MRI Research",
        publication_date=date(2026, 3, 15),
        source_url=HttpUrl("https://example.org/papers/mri-example"),
        authors=("Alice Smith", "Bob Jones"),
        provider_name="fake",
        provider_record_id="record-001",
    )


def resolve_example_record(
    provider: BibliographicProvider,
) -> ResolvedPaperMetadata:
    """Exercise the provider through its public contract"""

    return provider.resolve_by_doi("https://doi.org/10.1234/MRI.EXAMPLE")


def test_fake_provider_resolves_equivalent_doi_format() -> None:
    expected_record = make_metadata_record()
    provider = FakeBibliographicProvider([expected_record])

    resolved_record = resolve_example_record(provider)

    assert resolved_record == expected_record
    assert provider.name == "fake"


def test_fake_provider_raises_when_doi_is_unknown() -> None:
    provider = FakeBibliographicProvider([make_metadata_record()])

    with pytest.raises(
        BibliographicRecordNotFoundError,
        match="10.9999/missing",
    ):
        provider.resolve_by_doi("10.9999/MISSING")


def test_fake_provider_rejects_duplicate_canonical_dois() -> None:
    first_record = make_metadata_record(doi="10.1234/MRI.EXAMPLE")
    second_record = make_metadata_record(doi="https://doi.org/10.1234/mri.example")

    with pytest.raises(
        ValueError,
        match="Duplicate DOI in fake provider catalogue",
    ):
        FakeBibliographicProvider([first_record, second_record])
