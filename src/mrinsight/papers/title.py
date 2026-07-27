import hashlib
import re
import unicodedata
from datetime import date
from typing import Final

WHITESPACE_PATTERN: Final[re.Pattern[str]] = re.compile(r"\s+")
PRESERVED_PUNCTUATION: Final[frozenset[str]] = frozenset({"*"})

TITLE_FINGERPRINT_VERSION: Final[str] = "title-year-v1"


class InvalidTitleError(ValueError):
    """Raised when a paper title cannot be normalised."""


def normalize_title(value: str) -> str:
    """Return a canonical paper title for comparison and lookup.

    The canonical form: Unicode compatibility normalisation,
    Unicode-aware case folding, collapsed whitespace, and spaces in
    place of punctuation and control characters.
    """

    if not isinstance(value, str):
        raise InvalidTitleError("Paper title must be provided as a string.")

    candidate = unicodedata.normalize("NFKC", value).casefold()

    normalized_characters: list[str] = []

    for character in candidate:
        category = unicodedata.category(character)

        if character in PRESERVED_PUNCTUATION:
            normalized_characters.append(character)
        elif category.startswith(("P", "C")):
            normalized_characters.append(" ")
        else:
            normalized_characters.append(character)

    normalized = "".join(normalized_characters)
    normalized = WHITESPACE_PATTERN.sub(" ", normalized).strip()

    if not normalized:
        raise InvalidTitleError("Paper title cannot be empty.")

    return normalized


def build_title_year_fingerprint(
    title: str,
    publication_date: date | None,
) -> str | None:
    """Build a versioned duplicate-candidate fingerprint.

    A fingerprint is returned only when a publication date is available.
    Papers without sufficient metadata should not be automatically
    deduplicated using their title alone.
    """

    if publication_date is None:
        return None

    normalized_title = normalize_title(title)

    fingerprint_input = (
        f"{TITLE_FINGERPRINT_VERSION}|{publication_date.year}|{normalized_title}"
    )

    digest = hashlib.sha256(
        fingerprint_input.encode("utf-8"),
    ).hexdigest()

    return f"{TITLE_FINGERPRINT_VERSION}:{digest}"
