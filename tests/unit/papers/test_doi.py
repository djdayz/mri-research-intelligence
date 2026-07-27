import pytest

from mrinsight.papers import InvalidDOIError, normalize_doi


@pytest.mark.parametrize(
    ("raw_doi", "expected"),
    [
        ("10.1000/ABC123", "10.1000/abc123"),
        (" doi: 10.1000/ABC123 ", "10.1000/abc123"),
        (
            "https://doi.org/10.1000/ABC123",
            "10.1000/abc123",
        ),
        (
            "http://dx.doi.org/10.1000/ABC123",
            "10.1000/abc123",
        ),
        (
            "doi.org/10.1000/ABC123",
            "10.1000/abc123",
        ),
        (
            "https://doi.org/10.1000%2FABC123",
            "10.1000/abc123",
        ),
        (
            "<10.1000/ABC123>.",
            "10.1000/abc123",
        ),
    ],
)
def test_normalize_doi_returns_canonical_value(
    raw_doi: str,
    expected: str,
) -> None:
    assert normalize_doi(raw_doi) == expected


@pytest.mark.parametrize(
    "invalid_doi",
    [
        "",
        "   ",
        "not-a-doi",
        "11.1000/example",
        "10.1000",
        "10.12/example",
        "10.1000/example with spaces",
        "https://example.com/10.1000/example",
    ],
)
def test_normalize_doi_rejects_invalid_values(
    invalid_doi: str,
) -> None:
    with pytest.raises(InvalidDOIError):
        normalize_doi(invalid_doi)


def test_normalize_doi_rejects_non_string_value() -> None:
    with pytest.raises(
        InvalidDOIError,
        match="DOI must be provided as a string",
    ):
        normalize_doi(123)  # type: ignore[arg-type]


def test_normalize_doi_is_idempotent() -> None:
    raw_doi = "https://doi.org/10.1000/ABC123"

    normalised = normalize_doi(raw_doi)
    assert normalize_doi(normalised) == normalised
