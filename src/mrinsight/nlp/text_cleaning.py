import hashlib
import re
import unicodedata
from typing import Final

TEXT_CLEANER_VERSION: Final[str] = "scientific-text-v1"

HORIZONTAL_WHITESPACE_PATTERN: Final[re.Pattern[str]] = re.compile(r"[^\S\n]+")

EXCESS_BLANK_LINES_PATTERN: Final[re.Pattern[str]] = re.compile(r"\n{3,}")


class InvalidScientificTextError(ValueError):
    """Raised when scientific text cannot be cleaned."""


def clean_scientific_text(value: str) -> str:
    """Return deterministic text while preserving paragraph boundaries.

    The transformation performs Unicode canonical normalisation,
    standardises line endings, removes invisible control characters,
    collapses horizontal whitespace, and limits consecutive blank lines.
    """

    if not isinstance(value, str):
        raise InvalidScientificTextError(
            "Scientific text must be provided as a string."
        )

    candidate = unicodedata.normalize("NFC", value)
    candidate = candidate.replace("\r\n", "\n").replace("\r", "\n")

    retained_characters: list[str] = []

    for character in candidate:
        if character == "\n":
            retained_characters.append(character)
            continue

        category = unicodedata.category(character)

        if character.isspace():
            retained_characters.append(" ")
            continue

        if category.startswith("C"):
            continue

        retained_characters.append(character)

    candidate = "".join(retained_characters)

    cleaned_lines = [
        HORIZONTAL_WHITESPACE_PATTERN.sub(" ", line).strip()
        for line in candidate.split("\n")
    ]

    cleaned = "\n".join(cleaned_lines)
    cleaned = EXCESS_BLANK_LINES_PATTERN.sub("\n\n", cleaned)
    cleaned = cleaned.strip()

    if not cleaned:
        raise InvalidScientificTextError("Scientific text cannot be empty.")

    return cleaned


def compute_text_checksum(value: str) -> str:
    """Return a SHA-256 checksum of canonical scientific text."""

    cleaned_text = clean_scientific_text(value)

    return hashlib.sha256(cleaned_text.encode("utf-8")).hexdigest()
