from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from mrinsight.relevance import (
    RelevanceAssessmentServiceResult,
    RelevanceLabel,
)


class RelevanceAssessmentResponse(BaseModel):
    """Public response for one deterministic relevance assessment."""

    model_config = ConfigDict(extra="forbid")

    id: int
    paper_id: int
    paper_content_id: int
    analysis_scope: str
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
    cached: bool
    created_at: datetime
    updated_at: datetime
    tfidf_label: str | None
    tfidf_confidence: float | None

    @classmethod
    def from_result(
        cls,
        result: RelevanceAssessmentServiceResult,
    ) -> "RelevanceAssessmentResponse":
        """Create an API response from the application result."""

        assessment = result.assessment

        return cls(
            id=assessment.id,
            paper_id=assessment.paper_id,
            paper_content_id=assessment.paper_content_id,
            analysis_scope=assessment.analysis_scope.value,
            content_checksum=assessment.content_checksum,
            rule_score=assessment.rule_score,
            normalized_score=assessment.normalized_score,
            rule_label=assessment.rule_label,
            category_scores=assessment.category_scores,
            matched_concepts=assessment.matched_concepts,
            matched_terms=assessment.matched_terms,
            supporting_locations=assessment.supporting_locations,
            rule_version=assessment.rule_version,
            ontology_version=assessment.ontology_version,
            model_version=assessment.model_version,
            explanation=assessment.explanation,
            cached=result.cached,
            created_at=assessment.created_at,
            updated_at=assessment.updated_at,
            tfidf_label=assessment.tfidf_label,
            tfidf_confidence=assessment.tfidf_confidence,
        )
