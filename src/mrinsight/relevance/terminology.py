from __future__ import annotations

import json
import re
import unicodedata
from collections.abc import Iterable
from functools import lru_cache
from importlib.resources import files

from mrinsight.relevance.records import OntologyTerm, TermMatch


def normalize_match_text(value: str) -> str:
    """Normalize scientific text for deterministic terminology matching."""

    normalized = unicodedata.normalize("NFKC", value)
    translation: dict[str, str | int | None] = {
        "₂": "2",
        "₃": "3",
        "₄": "4",
        "–": "-",
        "—": "-",
        "‐": "-",
        "‑": "-",
        "−": "-",
        "μ": "u",
        "µ": "u",
    }
    normalized = normalized.translate(str.maketrans(translation))
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.casefold()


@lru_cache
def load_default_ontology() -> tuple[str, tuple[OntologyTerm, ...]]:
    """Load the bundled human-readable MRI/CVR ontology."""

    resource = files("mrinsight.relevance").joinpath("ontology.json")
    payload = json.loads(resource.read_text(encoding="utf-8"))

    return (
        str(payload["version"]),
        tuple(
            OntologyTerm(
                concept_id=str(concept["id"]),
                preferred_label=str(concept["preferred_label"]),
                category=str(concept["category"]),
                weight=float(concept["weight"]),
                match_policy=str(concept["match_policy"]),
                aliases=tuple(str(alias) for alias in concept["aliases"]),
                exclusions=tuple(
                    str(exclusion) for exclusion in concept.get("exclusions", [])
                ),
            )
            for concept in payload["concepts"]
        ),
    )


class TerminologyMatcher:
    """Boundary-aware matcher for the versioned relevance ontology."""

    def __init__(
        self,
        terms: Iterable[OntologyTerm],
    ) -> None:
        self._patterns = tuple(
            (
                term,
                alias,
                re.compile(_alias_pattern(alias)),
            )
            for term in sorted(
                terms,
                key=lambda value: (
                    value.category,
                    value.concept_id,
                ),
            )
            for alias in sorted(
                term.aliases,
                key=lambda value: (
                    -len(normalize_match_text(value)),
                    normalize_match_text(value),
                ),
            )
        )

    def find_matches(
        self,
        text: str,
    ) -> tuple[TermMatch, ...]:
        """Return deterministic non-overlapping terminology matches."""

        normalized = normalize_match_text(text)
        candidates: list[TermMatch] = []

        for term, alias, pattern in self._patterns:
            if any(
                exclusion in normalized
                for exclusion in (
                    normalize_match_text(item) for item in term.exclusions
                )
            ):
                continue

            for match in pattern.finditer(normalized):
                candidates.append(
                    TermMatch(
                        concept_id=term.concept_id,
                        preferred_label=term.preferred_label,
                        category=term.category,
                        matched_text=text[match.start() : match.end()],
                        alias=alias,
                        start_char=match.start(),
                        end_char=match.end(),
                        weight=term.weight,
                    )
                )

        return tuple(_deduplicate_overlaps(candidates))


def _alias_pattern(
    alias: str,
) -> str:
    """Build a boundary-aware regular expression for one alias."""

    normalized = normalize_match_text(alias)
    escaped = re.escape(normalized)
    if re.fullmatch(r"\d(?:\.\d)? t", normalized):
        escaped = escaped.replace(r"\ ", r"\s*")
        return rf"(?<![a-z0-9]){escaped}(?![a-z0-9])"

    escaped = escaped.replace(r"\-", r"[-\s]")
    escaped = escaped.replace(r"\ ", r"[\s\-]+")

    return rf"(?<![a-z0-9]){escaped}(?![a-z0-9])"


def _deduplicate_overlaps(
    candidates: list[TermMatch],
) -> list[TermMatch]:
    """Prefer longer and stronger matches when aliases overlap."""

    ordered = sorted(
        candidates,
        key=lambda match: (
            match.start_char,
            -(match.end_char - match.start_char),
            -match.weight,
            match.concept_id,
            normalize_match_text(match.alias),
        ),
    )
    accepted: list[TermMatch] = []

    for candidate in ordered:
        if any(
            candidate.start_char < existing.end_char
            and candidate.end_char > existing.start_char
            for existing in accepted
        ):
            continue
        accepted.append(candidate)

    return sorted(
        accepted,
        key=lambda match: (
            match.start_char,
            match.end_char,
            match.concept_id,
        ),
    )
