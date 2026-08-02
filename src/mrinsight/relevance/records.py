from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any

from mrinsight.papers import AnalysisScope


class RelevanceLabel(StrEnum):
    """Deterministic relevance label for MRI research triage."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NOT_RELEVANT = "not_relevant"


@dataclass(frozen=True, slots=True)
class OntologyTerm:
    """One canonical concept in the transparent terminology ontology."""

    concept_id: str
    preferred_label: str
    category: str
    weight: float
    match_policy: str
    aliases: tuple[str, ...]
    exclusions: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class TermMatch:
    """One matched alias occurrence."""

    concept_id: str
    preferred_label: str
    category: str
    matched_text: str
    alias: str
    start_char: int
    end_char: int
    weight: float

    def to_json(self) -> dict[str, Any]:
        """Return a JSON-safe representation."""

        return {
            "concept_id": self.concept_id,
            "preferred_label": self.preferred_label,
            "category": self.category,
            "matched_text": self.matched_text,
            "alias": self.alias,
            "start_char": self.start_char,
            "end_char": self.end_char,
            "weight": self.weight,
        }


@dataclass(frozen=True, slots=True)
class SupportingLocation:
    """Evidence location used to explain a relevance assessment."""

    source: str
    section: str | None
    chunk_id: int | None
    start_char: int
    end_char: int
    page_number: int | None
    end_page_number: int | None
    matched_term: str
    concept_id: str

    def to_json(self) -> dict[str, Any]:
        """Return a JSON-safe representation."""

        return {
            "source": self.source,
            "section": self.section,
            "chunk_id": self.chunk_id,
            "start_char": self.start_char,
            "end_char": self.end_char,
            "page_number": self.page_number,
            "end_page_number": self.end_page_number,
            "matched_term": self.matched_term,
            "concept_id": self.concept_id,
        }


@dataclass(frozen=True, slots=True)
class RelevanceScoreResult:
    """Typed deterministic relevance result before persistence."""

    total_score: float
    normalized_score: float
    label: RelevanceLabel
    matched_concepts: tuple[str, ...]
    matched_terms: tuple[TermMatch, ...]
    category_scores: dict[str, float]
    supporting_locations: tuple[SupportingLocation, ...]
    rules_version: str
    ontology_version: str
    explanation: str


@dataclass(frozen=True, slots=True)
class NewRelevanceAssessment:
    """Relevance assessment ready to be persisted."""

    paper_id: int
    paper_content_id: int
    analysis_scope: AnalysisScope
    content_checksum: str
    rule_score: float
    normalized_score: float
    rule_label: RelevanceLabel
    category_scores: dict[str, float]
    matched_concepts: tuple[str, ...]
    matched_terms: tuple[dict[str, Any], ...]
    supporting_locations: tuple[dict[str, Any], ...]
    rule_version: str
    ontology_version: str
    model_version: str
    explanation: str
    tfidf_label: str | None = None
    tfidf_confidence: float | None = None


@dataclass(frozen=True, slots=True)
class StoredRelevanceAssessment:
    """Persisted relevance assessment."""

    id: int
    paper_id: int
    paper_content_id: int
    analysis_scope: AnalysisScope
    content_checksum: str
    rule_score: float
    normalized_score: float
    rule_label: RelevanceLabel
    category_scores: dict[str, float]
    matched_concepts: tuple[str, ...]
    matched_terms: tuple[dict[str, Any], ...]
    supporting_locations: tuple[dict[str, Any], ...]
    rule_version: str
    ontology_version: str
    model_version: str
    explanation: str
    created_at: datetime
    updated_at: datetime
    tfidf_label: str | None = None
    tfidf_confidence: float | None = None


@dataclass(frozen=True, slots=True)
class RelevanceAssessmentServiceResult:
    """Application result for compute-or-retrieve relevance."""

    assessment: StoredRelevanceAssessment
    cached: bool
