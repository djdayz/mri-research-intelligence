import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Final

from mrinsight.nlp.sections import (
    DetectedParagraph,
    DetectedSection,
    detect_scientific_sections,
)
from mrinsight.papers import ContentType, SectionType

CHUNKER_VERSION: Final[str] = "section-paragraph-v1"

NON_WHITESPACE_PATTERN: Final[re.Pattern[str]] = re.compile(r"\S+")


@dataclass(frozen=True, slots=True)
class DetectedChunk:
    """One deterministic evidence chunk."""

    sequence_number: int
    section_type: SectionType
    heading: str | None
    text: str
    start_char: int
    end_char: int
    paragraph_start_sequence: int
    paragraph_end_sequence: int
    token_count: int


def count_whitespace_tokens(value: str) -> int:
    """Count non-whitespace spans using a transparent baseline."""

    return len(NON_WHITESPACE_PATTERN.findall(value))


def build_section_chunks(
    value: str,
    *,
    content_type: ContentType,
    max_tokens: int = 250,
    include_references: bool = False,
) -> tuple[DetectedChunk, ...]:
    """Detect sections and build bounded paragraph-aware chunks."""

    sections = detect_scientific_sections(
        value,
        content_type=content_type,
    )

    return chunk_detected_sections(
        sections,
        max_tokens=max_tokens,
        include_references=include_references,
    )


def chunk_detected_sections(
    sections: Sequence[DetectedSection],
    *,
    max_tokens: int = 250,
    include_references: bool = False,
) -> tuple[DetectedChunk, ...]:
    """Group consecutive paragraphs without crossing sections."""

    if max_tokens < 1:
        raise ValueError("max_tokens must be at least 1.")

    chunks: list[DetectedChunk] = []
    chunk_sequence = 1

    for section in sections:
        if section.section_type is SectionType.REFERENCES and not include_references:
            continue

        current_paragraphs: list[DetectedParagraph] = []
        current_token_count = 0

        for paragraph in section.paragraphs:
            paragraph_token_count = count_whitespace_tokens(paragraph.text)

            if (
                current_paragraphs
                and current_token_count + paragraph_token_count > max_tokens
            ):
                chunks.append(
                    _build_chunk(
                        sequence_number=chunk_sequence,
                        section=section,
                        paragraphs=current_paragraphs,
                    )
                )
                chunk_sequence += 1
                current_paragraphs = []
                current_token_count = 0

            current_paragraphs.append(paragraph)
            current_token_count += paragraph_token_count

            if paragraph_token_count > max_tokens:
                chunks.append(
                    _build_chunk(
                        sequence_number=chunk_sequence,
                        section=section,
                        paragraphs=current_paragraphs,
                    )
                )
                chunk_sequence += 1
                current_paragraphs = []
                current_token_count = 0

        if current_paragraphs:
            chunks.append(
                _build_chunk(
                    sequence_number=chunk_sequence,
                    section=section,
                    paragraphs=current_paragraphs,
                )
            )
            chunk_sequence += 1

    return tuple(chunks)


def _build_chunk(
    *,
    sequence_number: int,
    section: DetectedSection,
    paragraphs: Sequence[DetectedParagraph],
) -> DetectedChunk:
    """Build one chunk from consecutive source paragraphs."""

    if not paragraphs:
        raise ValueError("A chunk requires at least one paragraph.")

    text = "\n\n".join(paragraph.text for paragraph in paragraphs)

    return DetectedChunk(
        sequence_number=sequence_number,
        section_type=section.section_type,
        heading=section.heading,
        text=text,
        start_char=paragraphs[0].start_char,
        end_char=paragraphs[-1].end_char,
        paragraph_start_sequence=(paragraphs[0].sequence_number),
        paragraph_end_sequence=(paragraphs[-1].sequence_number),
        token_count=count_whitespace_tokens(text),
    )
