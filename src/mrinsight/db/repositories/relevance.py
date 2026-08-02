from typing import Any, cast

from sqlalchemy import select
from sqlalchemy.orm import Session

from mrinsight.db.models import PaperRelevanceAssessment
from mrinsight.papers import AnalysisScope
from mrinsight.relevance import (
    NewRelevanceAssessment,
    RelevanceLabel,
    StoredRelevanceAssessment,
)


class SqlAlchemyRelevanceAssessmentRepository:
    """Persist relevance assessments using SQLAlchemy."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_current(
        self,
        *,
        paper_id: int,
        paper_content_id: int,
        analysis_scope: AnalysisScope,
        content_checksum: str,
        rule_version: str,
        ontology_version: str,
        model_version: str,
    ) -> StoredRelevanceAssessment | None:
        """Return a cached assessment for the exact reproducibility identity."""

        statement = select(PaperRelevanceAssessment).where(
            PaperRelevanceAssessment.paper_id == paper_id,
            PaperRelevanceAssessment.paper_content_id == paper_content_id,
            PaperRelevanceAssessment.analysis_scope == analysis_scope.value,
            PaperRelevanceAssessment.content_checksum == content_checksum,
            PaperRelevanceAssessment.rule_version == rule_version,
            PaperRelevanceAssessment.ontology_version == ontology_version,
            PaperRelevanceAssessment.model_version == model_version,
        )

        model = self._session.execute(statement).scalar_one_or_none()

        if model is None:
            return None

        return self._to_stored_assessment(model)

    def add(
        self,
        assessment: NewRelevanceAssessment,
    ) -> StoredRelevanceAssessment:
        """Persist a new assessment and flush without committing."""

        model = PaperRelevanceAssessment(
            paper_id=assessment.paper_id,
            paper_content_id=assessment.paper_content_id,
            analysis_scope=assessment.analysis_scope.value,
            content_checksum=assessment.content_checksum,
            rule_score=assessment.rule_score,
            normalized_score=assessment.normalized_score,
            rule_label=assessment.rule_label.value,
            category_scores=assessment.category_scores,
            matched_concepts=list(assessment.matched_concepts),
            matched_terms=list(assessment.matched_terms),
            supporting_locations=list(assessment.supporting_locations),
            rule_version=assessment.rule_version,
            ontology_version=assessment.ontology_version,
            model_version=assessment.model_version,
            tfidf_label=assessment.tfidf_label,
            tfidf_confidence=assessment.tfidf_confidence,
            explanation=assessment.explanation,
        )

        self._session.add(model)
        self._session.flush()
        self._session.refresh(model)

        return self._to_stored_assessment(model)

    @staticmethod
    def _to_stored_assessment(
        model: PaperRelevanceAssessment,
    ) -> StoredRelevanceAssessment:
        """Translate an ORM model into an application value."""

        return StoredRelevanceAssessment(
            id=model.id,
            paper_id=model.paper_id,
            paper_content_id=model.paper_content_id,
            analysis_scope=AnalysisScope(model.analysis_scope),
            content_checksum=model.content_checksum,
            rule_score=model.rule_score,
            normalized_score=model.normalized_score,
            rule_label=RelevanceLabel(model.rule_label),
            category_scores=dict(model.category_scores),
            matched_concepts=tuple(model.matched_concepts),
            matched_terms=tuple(
                cast(dict[str, Any], item) for item in model.matched_terms
            ),
            supporting_locations=tuple(
                cast(dict[str, Any], item) for item in model.supporting_locations
            ),
            rule_version=model.rule_version,
            ontology_version=model.ontology_version,
            model_version=model.model_version,
            tfidf_label=model.tfidf_label,
            tfidf_confidence=model.tfidf_confidence,
            explanation=model.explanation,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
