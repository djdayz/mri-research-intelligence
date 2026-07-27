from datetime import date

import pytest

from mrinsight.papers import (
    InvalidTitleError,
    build_title_year_fingerprint,
    normalize_title,
)


@pytest.mark.parametrize(
    ("raw_title", "expected"),
    [
        (
            "Deep-Learning–Based MRI Reconstruction: A Multi-Centre Study",
            "deep learning based mri reconstruction a multi centre study",
        ),
        (
            "  DEEP   LEARNING\nFOR MRI  ",
            "deep learning for mri",
        ),
        (
            "ＭＲＩ Reconstruction",
            "mri reconstruction",
        ),
        (
            "T2*-weighted MRI",
            "t2* weighted mri",
        ),
        (
            "C++ Methods for MRI",
            "c++ methods for mri",
        ),
        (
            "Uncertainty = Error ± Variability",
            "uncertainty = error ± variability",
        ),
    ],
)
def test_normalize_title_returns_canonical_value(
    raw_title: str,
    expected: str,
) -> None:
    assert normalize_title(raw_title) == expected


@pytest.mark.parametrize(
    "invalid_title",
    [
        "",
        "   ",
        "...",
        "---",
        ":\n;",
    ],
)
def test_normalize_title_rejects_empty_canonical_titles(
    invalid_title: str,
) -> None:
    with pytest.raises(InvalidTitleError):
        normalize_title(invalid_title)


def test_normalize_title_rejects_non_string_value() -> None:
    with pytest.raises(
        InvalidTitleError,
        match="Paper title must be provided as a string",
    ):
        normalize_title(123)  # type: ignore[arg-type]


def test_normalize_title_is_idempotent() -> None:
    raw_title = "Deep-Learning–Based MRI Reconstruction: A Multi-Centre Study"

    normalized_once = normalize_title(raw_title)
    normalized_twice = normalize_title(normalized_once)

    assert normalized_twice == normalized_once


def test_title_fingerprint_is_stable_across_formatting_variations() -> None:
    publication_date = date(2026, 4, 15)

    first = build_title_year_fingerprint(
        "Deep-Learning MRI Reconstruction",
        publication_date,
    )
    second = build_title_year_fingerprint(
        "deep learning—mri reconstruction",
        publication_date,
    )

    assert first == second


def test_title_fingerprint_changes_for_different_years() -> None:
    title = "Deep Learning for MRI Reconstruction"

    fingerprint_2025 = build_title_year_fingerprint(
        title,
        date(2025, 5, 1),
    )
    fingerprint_2026 = build_title_year_fingerprint(
        title,
        date(2026, 5, 1),
    )

    assert fingerprint_2025 != fingerprint_2026


def test_title_fingerprint_is_not_created_without_date() -> None:
    assert (
        build_title_year_fingerprint(
            "Deep Learning for MRI Reconstruction",
            None,
        )
        is None
    )
