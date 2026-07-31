import pytest

from mrinsight.nlp import (
    build_section_chunks,
    clean_scientific_text,
    count_whitespace_tokens,
)
from mrinsight.papers import ContentType, SectionType


def test_whitespace_token_count_is_transparent() -> None:
    assert count_whitespace_tokens("MRI reconstruction improved by 18%.") == 5


def test_chunks_do_not_cross_section_boundaries() -> None:
    text = """Methods
Images were acquired at 3 T.

Preprocessing included motion correction.

Results
The method reduced RMSE by 18%."""

    chunks = build_section_chunks(
        text,
        content_type=ContentType.FULL_TEXT,
        max_tokens=100,
    )

    assert len(chunks) == 2

    assert chunks[0].section_type is SectionType.METHODS
    assert chunks[0].text == (
        "Images were acquired at 3 T.\n\nPreprocessing included motion correction."
    )

    assert chunks[1].section_type is SectionType.RESULTS
    assert chunks[1].text == ("The method reduced RMSE by 18%.")


def test_chunker_splits_at_paragraph_boundaries() -> None:
    text = """Methods
One two three four.

Five six seven eight.

Nine ten eleven twelve."""

    chunks = build_section_chunks(
        text,
        content_type=ContentType.FULL_TEXT,
        max_tokens=8,
    )

    assert len(chunks) == 2

    assert chunks[0].text == ("One two three four.\n\nFive six seven eight.")
    assert chunks[0].token_count == 8

    assert chunks[1].text == ("Nine ten eleven twelve.")
    assert chunks[1].token_count == 4


def test_chunk_records_paragraph_range_and_offsets() -> None:
    text = """Methods
First MRI paragraph.

Second MRI paragraph."""

    chunks = build_section_chunks(
        text,
        content_type=ContentType.FULL_TEXT,
        max_tokens=100,
    )

    assert len(chunks) == 1

    chunk = chunks[0]
    assert chunk.paragraph_start_sequence == 1
    assert chunk.paragraph_end_sequence == 2
    assert clean_scientific_text(text)[chunk.start_char : chunk.end_char] == (
        "First MRI paragraph.\n\nSecond MRI paragraph."
    )


def test_references_are_excluded_by_default() -> None:
    text = """Results
The method reduced error.

References
Example reference one.
Example reference two."""

    chunks = build_section_chunks(
        text,
        content_type=ContentType.FULL_TEXT,
    )

    assert len(chunks) == 1
    assert chunks[0].section_type is SectionType.RESULTS


def test_references_can_be_included_explicitly() -> None:
    text = """Results
The method reduced error.

References
Example reference one."""

    chunks = build_section_chunks(
        text,
        content_type=ContentType.FULL_TEXT,
        include_references=True,
    )

    assert [chunk.section_type for chunk in chunks] == [
        SectionType.RESULTS,
        SectionType.REFERENCES,
    ]


def test_oversized_paragraph_is_kept_intact() -> None:
    text = """Methods
One two three four five six seven eight."""

    chunks = build_section_chunks(
        text,
        content_type=ContentType.FULL_TEXT,
        max_tokens=4,
    )

    assert len(chunks) == 1
    assert chunks[0].token_count == 8
    assert chunks[0].text == ("One two three four five six seven eight.")


def test_chunker_rejects_invalid_maximum() -> None:
    with pytest.raises(
        ValueError,
        match="max_tokens must be at least 1",
    ):
        build_section_chunks(
            "An abstract.",
            content_type=ContentType.ABSTRACT,
            max_tokens=0,
        )
