import pytest

from mrinsight.nlp import (
    InvalidScientificTextError,
    clean_scientific_text,
    compute_text_checksum,
)


def test_clean_scientific_text_normalizes_whitespace() -> None:
    raw_text = "  MRI\t  reconstruction\r\n\r\nResults:\u200b   RMSE improved.  "

    cleaned = clean_scientific_text(raw_text)

    assert cleaned == ("MRI reconstruction\n\nResults: RMSE improved.")


def test_clean_scientific_text_preserves_scientific_symbols() -> None:
    raw_text = "T2*-weighted MRI showed a 12.5% ± 1.2% improvement for ΔCO₂."

    assert clean_scientific_text(raw_text) == raw_text


def test_clean_scientific_text_limits_blank_lines() -> None:
    raw_text = "Methods\n\n\n\n\nResults"

    assert clean_scientific_text(raw_text) == ("Methods\n\nResults")


@pytest.mark.parametrize(
    "invalid_text",
    [
        "",
        "   ",
        "\n\n",
        "\u200b",
    ],
)
def test_clean_scientific_text_rejects_empty_result(
    invalid_text: str,
) -> None:
    with pytest.raises(InvalidScientificTextError):
        clean_scientific_text(invalid_text)


def test_clean_scientific_text_rejects_non_string_value() -> None:
    with pytest.raises(
        InvalidScientificTextError,
        match="must be provided as a string",
    ):
        clean_scientific_text(123)  # type: ignore[arg-type]


def test_checksum_is_stable_for_equivalent_formatting() -> None:
    first = "MRI   reconstruction\r\n\r\nResults"
    second = "MRI reconstruction\n\nResults"

    assert compute_text_checksum(first) == compute_text_checksum(second)


def test_checksum_changes_when_content_changes() -> None:
    first = compute_text_checksum("The model achieved an RMSE of 0.20.")
    second = compute_text_checksum("The model achieved an RMSE of 0.30.")

    assert first != second


def test_clean_scientific_text_is_idempotent() -> None:
    raw_text = "  Methods\tsection\r\n\r\n\r\nResults\u200b section  "

    cleaned_once = clean_scientific_text(raw_text)
    cleaned_twice = clean_scientific_text(cleaned_once)

    assert cleaned_twice == cleaned_once
