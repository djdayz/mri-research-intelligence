import re
import unicodedata
from typing import Final
from urllib.parse import unquote, urlsplit

DOI_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"^10\.\d{4,9}/\S+$",
)

DOI_LABEL_PREFIX: Final[re.Pattern[str]] = re.compile(
    r"^doi\s*:\s*",
    re.IGNORECASE,
)

DOI_RESOLVER_PREFIX: Final[re.Pattern[str]] = re.compile(
    r"^(?:www\.)?(?:dx\.)?doi\.org/",
    re.IGNORECASE,
)

DOI_RESOLVER_HOSTS: Final[frozenset[str]] = frozenset(
    {
        "doi.org",
        "www.doi.org",
        "dx.doi.org",
        "www.dx.doi.org",
    }
)

OUTER_WRAPPERS: Final[tuple[tuple[str, str], ...]] = (
    ("<", ">"),
    ("[", "]"),
    ("{", "}"),
    ("(", ")"),
    ('"', '"'),
    ("'", "'"),
)


class InvalidDOIError(ValueError):
    """Raised when a value cannot be normalised into a valid DOI"""


def normalize_doi(value: str) -> str:
    """Return a canonical DOI suitable for comparison and storage

    The canonical form: lowercase and excludes DOI labels, resolver URLs,
    surrounding citation wrappers and common trailing citation punctuation
    """

    if not isinstance(value, str):
        raise InvalidDOIError("DOI must be provided as a string.")

    candidate = unicodedata.normalize("NFKC", value)
    candidate = unquote(candidate)
    candidate = _trim_citation_formatting(candidate)

    if not candidate:
        raise InvalidDOIError("DOI cannot be empty.")

    candidate = DOI_LABEL_PREFIX.sub("", candidate, count=1)
    candidate = _trim_citation_formatting(candidate)

    candidate = _remove_resolver_url(candidate)
    candidate = _trim_citation_formatting(candidate)
    candidate = candidate.lower()

    if not DOI_PATTERN.fullmatch(candidate):
        raise InvalidDOIError(f"Invalid DOI: {value!r}")

    return candidate


def _remove_resolver_url(value: str) -> str:
    """Remove a recognised doi.org resolver prefix"""

    parsed = urlsplit(value)

    if parsed.scheme.lower() in {"http", "https"}:
        hostname = (parsed.hostname or "").lower()

        if hostname in DOI_RESOLVER_HOSTS:
            return parsed.path.lstrip("/")

        return value

    return DOI_RESOLVER_PREFIX.sub("", value, count=1)


def _trim_citation_formatting(value: str) -> str:
    """Remove whitespace, outer wrappers and common citation punctuation"""

    candidate = value.strip().rstrip(".,;")

    for opening, closing in OUTER_WRAPPERS:
        if candidate.startswith(opening) and candidate.endswith(closing):
            candidate = candidate[len(opening) : len(candidate) - len(closing)].strip()
            break

    return candidate.rstrip(".,;")
