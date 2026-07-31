import pytest

from mrinsight.nlp import (
    classify_section_heading,
    detect_scientific_sections,
    normalize_section_heading,
)
from mrinsight.papers import ContentType, SectionType


@pytest.mark.parametrize(
    ("heading", "expected"),
    [
        ("2. Materials & Methods", SectionType.METHODS),
        ("METHODS:", SectionType.METHODS),
        ("III. Results", SectionType.RESULTS),
        ("Results and Discussion", SectionType.DISCUSSION),
        ("Study Limitations", SectionType.LIMITATIONS),
        ("Conclusions", SectionType.CONCLUSION),
        ("Bibliography", SectionType.REFERENCES),
    ],
)
def test_classify_section_heading_recognizes_aliases(
    heading: str,
    expected: SectionType,
) -> None:
    assert classify_section_heading(heading) is expected


def test_normalize_section_heading_removes_numbering() -> None:
    assert (
        normalize_section_heading("Section 2.1: Materials & Methods")
        == "materials and methods"
    )


def test_sentence_is_not_classified_as_heading() -> None:
    assert classify_section_heading("The results showed a lower RMSE.") is None


def test_unstructured_abstract_uses_abstract_section() -> None:
    text = (
        "We evaluated an MRI reconstruction model.\n\n"
        "The model reduced RMSE on the test dataset."
    )

    sections = detect_scientific_sections(
        text,
        content_type=ContentType.ABSTRACT,
    )

    assert len(sections) == 1

    section = sections[0]

    assert section.section_type is SectionType.ABSTRACT
    assert section.heading is None
    assert len(section.paragraphs) == 2
    assert section.paragraphs[0].sequence_number == 1
    assert section.paragraphs[1].sequence_number == 2


def test_structured_abstract_detects_sections() -> None:
    text = """Background
Long MRI acquisition times limit clinical use.

Methods
We trained a reconstruction network on 500 scans.

Results
The method reduced RMSE by 18%.

Conclusions
The method improved reconstruction accuracy."""

    sections = detect_scientific_sections(
        text,
        content_type=ContentType.ABSTRACT,
    )

    assert [section.section_type for section in sections] == [
        SectionType.BACKGROUND,
        SectionType.METHODS,
        SectionType.RESULTS,
        SectionType.CONCLUSION,
    ]

    assert sections[1].heading == "Methods"
    assert sections[1].paragraphs[0].text == (
        "We trained a reconstruction network on 500 scans."
    )

    assert sections[2].paragraphs[0].text == ("The method reduced RMSE by 18%.")


def test_full_text_detects_numbered_sections() -> None:
    text = """An MRI Reconstruction Study

1. Introduction
MRI acquisition time remains a major limitation.

2. Materials and Methods
Images were acquired at 3 T.
The model was trained using five-fold validation.

3. Results
The proposed method achieved an RMSE of 0.18.

4. Discussion
Performance improved relative to the baseline.

5. Conclusions
The method reduced reconstruction error.

References
Example reference."""

    sections = detect_scientific_sections(
        text,
        content_type=ContentType.FULL_TEXT,
    )

    assert [section.section_type for section in sections] == [
        SectionType.OTHER,
        SectionType.INTRODUCTION,
        SectionType.METHODS,
        SectionType.RESULTS,
        SectionType.DISCUSSION,
        SectionType.CONCLUSION,
        SectionType.REFERENCES,
    ]

    assert sections[0].heading is None
    assert sections[0].paragraphs[0].text == ("An MRI Reconstruction Study")

    assert len(sections[2].paragraphs) == 1
    assert sections[2].paragraphs[0].text == (
        "Images were acquired at 3 T. The model was trained using five-fold validation."
    )


def test_paragraph_offsets_reference_cleaned_text() -> None:
    text = """Methods
MRI data were acquired at 3 T.

Results
RMSE decreased to 0.20."""

    sections = detect_scientific_sections(
        text,
        content_type=ContentType.FULL_TEXT,
    )

    methods_paragraph = sections[0].paragraphs[0]
    results_paragraph = sections[1].paragraphs[0]

    methods_source = text[methods_paragraph.start_char : methods_paragraph.end_char]
    results_source = text[results_paragraph.start_char : results_paragraph.end_char]

    assert methods_source == ("MRI data were acquired at 3 T.")
    assert results_source == "RMSE decreased to 0.20."


def test_multiple_paragraphs_remain_in_same_section() -> None:
    text = """Discussion
The model performed better than the baseline.

Performance decreased on external data."""

    sections = detect_scientific_sections(
        text,
        content_type=ContentType.FULL_TEXT,
    )

    assert len(sections) == 1

    section = sections[0]

    assert section.section_type is SectionType.DISCUSSION
    assert len(section.paragraphs) == 2
    assert section.paragraphs[0].sequence_number == 1
    assert section.paragraphs[1].sequence_number == 2
