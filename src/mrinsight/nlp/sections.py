import re
import unicodedata
from dataclasses import dataclass
from typing import Final

from mrinsight.nlp.text_cleaning import clean_scientific_text
from mrinsight.papers import ContentType, SectionType

SECTION_NUMBER_PREFIX: Final[re.Pattern[str]] = re.compile(
    r"""
    ^\s*
    (?:
        section\s+
    )?
    (?:
        (?:\d+(?:\.\d+)*|[ivxlcdm]+)
        (?:
            \s*[.):\-]\s*
            |
            \s+
        )
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)

WHITESPACE_PATTERN: Final[re.Pattern[str]] = re.compile(r"\s+")


SECTION_HEADING_ALIASES: Final[dict[SectionType, frozenset[str]]] = {
    SectionType.ABSTRACT: frozenset(
        {
            "abstract",
            "summary",
        }
    ),
    SectionType.BACKGROUND: frozenset(
        {
            "background",
            "aim",
            "aims",
            "objective",
            "objectives",
            "purpose",
        }
    ),
    SectionType.INTRODUCTION: frozenset(
        {
            "introduction",
            "introduction and background",
        }
    ),
    SectionType.METHODS: frozenset(
        {
            "methods",
            "methodology",
            "materials and methods",
            "patients and methods",
            "subjects and methods",
            "data and methods",
            "experimental procedures",
            "study design",
        }
    ),
    SectionType.RESULTS: frozenset(
        {
            "results",
            "findings",
        }
    ),
    SectionType.DISCUSSION: frozenset(
        {
            "discussion",
            "results and discussion",
            "discussion and interpretation",
        }
    ),
    SectionType.LIMITATIONS: frozenset(
        {
            "limitations",
            "study limitations",
            "strengths and limitations",
        }
    ),
    SectionType.CONCLUSION: frozenset(
        {
            "conclusion",
            "conclusions",
            "concluding remarks",
        }
    ),
    SectionType.REFERENCES: frozenset(
        {
            "references",
            "bibliography",
        }
    ),
}


HEADING_TO_SECTION: Final[dict[str, SectionType]] = {
    alias: section_type
    for section_type, aliases in SECTION_HEADING_ALIASES.items()
    for alias in aliases
}


@dataclass(frozen=True, slots=True)
class DetectedParagraph:
    """One paragraph and its position in the cleaned source text."""

    sequence_number: int
    text: str
    start_char: int
    end_char: int


@dataclass(frozen=True, slots=True)
class DetectedSection:
    """One detected scientific-document section."""

    sequence_number: int
    section_type: SectionType
    heading: str | None
    paragraphs: tuple[DetectedParagraph, ...]


def normalize_section_heading(value: str) -> str:
    """Return a canonical heading used for section classification."""

    candidate = unicodedata.normalize("NFKC", value)
    candidate = candidate.casefold().strip()
    candidate = SECTION_NUMBER_PREFIX.sub("", candidate)
    candidate = candidate.replace("&", " and ")

    normalized_characters: list[str] = []

    for character in candidate:
        category = unicodedata.category(character)

        if category.startswith(("P", "C")):
            normalized_characters.append(" ")
        else:
            normalized_characters.append(character)

    normalized = "".join(normalized_characters)
    normalized = WHITESPACE_PATTERN.sub(" ", normalized)

    return normalized.strip()


def classify_section_heading(
    value: str,
) -> SectionType | None:
    """Map a recognised heading to a canonical section type."""

    normalized_heading = normalize_section_heading(value)

    return HEADING_TO_SECTION.get(normalized_heading)


def detect_scientific_sections(
    value: str,
    *,
    content_type: ContentType,
) -> tuple[DetectedSection, ...]:
    """Detect sections and paragraphs in cleaned scientific text.

    Only standalone lines matching known heading aliases are treated
    as headings. Unknown text is retained under the current section.
    """

    cleaned_text = clean_scientific_text(value)

    default_section_type = (
        SectionType.ABSTRACT
        if content_type is ContentType.ABSTRACT
        else SectionType.OTHER
    )

    sections: list[DetectedSection] = []
    current_section_type = default_section_type
    current_heading: str | None = None
    current_paragraphs: list[DetectedParagraph] = []

    paragraph_lines: list[tuple[str, int, int]] = []
    paragraph_sequence = 1

    def flush_paragraph() -> None:
        nonlocal paragraph_sequence

        if not paragraph_lines:
            return

        paragraph_text = " ".join(line.strip() for line, _, _ in paragraph_lines)

        current_paragraphs.append(
            DetectedParagraph(
                sequence_number=paragraph_sequence,
                text=paragraph_text,
                start_char=paragraph_lines[0][1],
                end_char=paragraph_lines[-1][2],
            )
        )

        paragraph_sequence += 1
        paragraph_lines.clear()

    def flush_section() -> None:
        nonlocal current_paragraphs

        if not current_paragraphs:
            return

        sections.append(
            DetectedSection(
                sequence_number=len(sections) + 1,
                section_type=current_section_type,
                heading=current_heading,
                paragraphs=tuple(current_paragraphs),
            )
        )

        current_paragraphs = []

    for line, start_char, end_char in _iter_lines_with_offsets(cleaned_text):
        stripped_line = line.strip()

        if not stripped_line:
            flush_paragraph()
            continue

        detected_type = classify_section_heading(stripped_line)

        if detected_type is not None:
            flush_paragraph()
            flush_section()

            current_section_type = detected_type
            current_heading = stripped_line
            continue

        paragraph_lines.append(
            (
                stripped_line,
                start_char,
                end_char,
            )
        )

    flush_paragraph()
    flush_section()

    return tuple(sections)


def _iter_lines_with_offsets(
    value: str,
) -> tuple[tuple[str, int, int], ...]:
    """Return lines with start-inclusive and end-exclusive offsets."""

    lines: list[tuple[str, int, int]] = []
    offset = 0

    for line_with_ending in value.splitlines(keepends=True):
        line = line_with_ending.rstrip("\n")
        start_char = offset
        end_char = start_char + len(line)

        lines.append(
            (
                line,
                start_char,
                end_char,
            )
        )

        offset += len(line_with_ending)

    return tuple(lines)
