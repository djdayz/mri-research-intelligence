from typing import Protocol

from mrinsight.papers import AnalysisScope
from mrinsight.relevance.records import (
    NewRelevanceAssessment,
    StoredRelevanceAssessment,
)


class RelevanceAssessmentRepository(Protocol):
    """Persistence contract for relevance assessments."""

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

    def add(
        self,
        assessment: NewRelevanceAssessment,
    ) -> StoredRelevanceAssessment:
        """Persist a new assessment without committing."""
