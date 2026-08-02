from __future__ import annotations

from collections import Counter
from collections.abc import Sequence

from mrinsight.papers import SectionType, StoredPaperChunk
from mrinsight.papers.records import StoredPaper
from mrinsight.relevance.records import (
    RelevanceLabel,
    RelevanceScoreResult,
    SupportingLocation,
    TermMatch,
)
from mrinsight.relevance.terminology import (
    TerminologyMatcher,
    load_default_ontology,
)

RELEVANCE_RULES_VERSION = "mri-cvr-relevance-rules-v1"
RELEVANCE_MODEL_VERSION = "deterministic-relevance-v1"

_SECTION_WEIGHTS: dict[SectionType, float] = {
    SectionType.ABSTRACT: 1.2,
    SectionType.BACKGROUND: 0.9,
    SectionType.INTRODUCTION: 0.9,
    SectionType.METHODS: 1.25,
    SectionType.RESULTS: 1.15,
    SectionType.DISCUSSION: 1.0,
    SectionType.LIMITATIONS: 0.75,
    SectionType.CONCLUSION: 0.85,
    SectionType.REFERENCES: 0.05,
    SectionType.OTHER: 0.65,
}


class RuleBasedRelevanceScorer:
    """Transparent deterministic scorer for MRI/CVR research relevance."""

    def __init__(self) -> None:
        ontology_version, terms = load_default_ontology()
        self._ontology_version = ontology_version
        self._matcher = TerminologyMatcher(terms)

    @property
    def ontology_version(self) -> str:
        """Return the ontology version used by this scorer."""

        return self._ontology_version

    def score(
        self,
        *,
        paper: StoredPaper,
        selected_text: str,
        chunks: Sequence[StoredPaperChunk],
    ) -> RelevanceScoreResult:
        """Score paper relevance using metadata and selected analysis evidence."""

        del selected_text

        weighted_matches: list[tuple[TermMatch, float, SupportingLocation]] = []

        weighted_matches.extend(
            self._score_text(
                source="title",
                text=paper.title,
                source_weight=2.0,
                section=None,
                chunk=None,
            )
        )

        if paper.abstract:
            weighted_matches.extend(
                self._score_text(
                    source="abstract_metadata",
                    text=paper.abstract,
                    source_weight=1.1,
                    section=SectionType.ABSTRACT.value,
                    chunk=None,
                )
            )

        for chunk in chunks:
            if chunk.section_type is SectionType.REFERENCES:
                continue
            weighted_matches.extend(
                self._score_text(
                    source="chunk",
                    text=chunk.text,
                    source_weight=_SECTION_WEIGHTS[chunk.section_type],
                    section=chunk.section_type.value,
                    chunk=chunk,
                )
            )

        category_scores: dict[str, float] = {}
        concept_counter: Counter[str] = Counter()
        total_score = 0.0

        for match, weight, _location in weighted_matches:
            total_score += weight
            category_scores[match.category] = (
                category_scores.get(match.category, 0.0) + weight
            )
            concept_counter[match.concept_id] += 1

        matched_concepts = tuple(sorted(concept_counter))
        total_score += _combination_bonus(matched_concepts, category_scores)
        total_score = round(total_score, 3)
        normalized_score = round(min(total_score / 80.0, 1.0), 3)
        label = _label_for_score(
            normalized_score,
            matched_concepts,
            category_scores,
        )

        explanation = _build_explanation(
            label=label,
            matched_concepts=matched_concepts,
            category_scores=category_scores,
        )

        return RelevanceScoreResult(
            total_score=total_score,
            normalized_score=normalized_score,
            label=label,
            matched_concepts=matched_concepts,
            matched_terms=tuple(
                match for match, _weight, _location in weighted_matches
            ),
            category_scores={
                category: round(score, 3)
                for category, score in sorted(category_scores.items())
            },
            supporting_locations=tuple(
                location for _match, _weight, location in weighted_matches[:25]
            ),
            rules_version=RELEVANCE_RULES_VERSION,
            ontology_version=self._ontology_version,
            explanation=explanation,
        )

    def _score_text(
        self,
        *,
        source: str,
        text: str,
        source_weight: float,
        section: str | None,
        chunk: StoredPaperChunk | None,
    ) -> list[tuple[TermMatch, float, SupportingLocation]]:
        """Match and weight one source string."""

        weighted: list[tuple[TermMatch, float, SupportingLocation]] = []

        for match in self._matcher.find_matches(text):
            weight = match.weight * source_weight
            offset = chunk.start_char if chunk is not None else 0
            weighted.append(
                (
                    match,
                    weight,
                    SupportingLocation(
                        source=source,
                        section=section,
                        chunk_id=chunk.id if chunk is not None else None,
                        start_char=offset + match.start_char,
                        end_char=offset + match.end_char,
                        page_number=chunk.page_number if chunk is not None else None,
                        end_page_number=(
                            chunk.end_page_number if chunk is not None else None
                        ),
                        matched_term=match.matched_text,
                        concept_id=match.concept_id,
                    ),
                )
            )

        return weighted


def _combination_bonus(
    matched_concepts: tuple[str, ...],
    category_scores: dict[str, float],
) -> float:
    """Reward clinically useful concept combinations and penalize ML-only hits."""

    concepts = set(matched_concepts)
    bonus = 0.0

    if {"mri_general", "cvr"}.issubset(concepts):
        bonus += 24.0
    if {"mri_general", "machine_learning"}.issubset(concepts):
        bonus += 14.0
    if {"mri_general", "mri_reconstruction"}.issubset(concepts):
        bonus += 18.0
    if concepts == {"machine_learning"}:
        bonus -= category_scores.get("machine_learning", 0.0)

    return bonus


def _label_for_score(
    normalized_score: float,
    matched_concepts: tuple[str, ...],
    category_scores: dict[str, float],
) -> RelevanceLabel:
    """Convert score and concept mix into a stable label."""

    if not matched_concepts:
        return RelevanceLabel.NOT_RELEVANT
    if matched_concepts == ("machine_learning",):
        return RelevanceLabel.NOT_RELEVANT
    if normalized_score >= 0.7:
        return RelevanceLabel.HIGH
    if normalized_score >= 0.35:
        return RelevanceLabel.MEDIUM
    if category_scores.get("mri", 0.0) > 0:
        return RelevanceLabel.LOW
    return RelevanceLabel.NOT_RELEVANT


def _build_explanation(
    *,
    label: RelevanceLabel,
    matched_concepts: tuple[str, ...],
    category_scores: dict[str, float],
) -> str:
    """Create a short transparent score explanation."""

    if label is RelevanceLabel.NOT_RELEVANT:
        return "No MRI-relevant concept combination was found."

    categories = ", ".join(
        f"{category}={score:.1f}" for category, score in sorted(category_scores.items())
    )
    concepts = ", ".join(matched_concepts)

    return (
        f"Label {label.value} from matched concepts [{concepts}] "
        f"with category scores [{categories}]."
    )
