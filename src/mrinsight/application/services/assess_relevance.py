from dataclasses import dataclass

from mrinsight.application.services.ingest_full_text import PaperNotFoundError
from mrinsight.application.services.select_analysis_content import (
    NoAnalyzableContentError,
    SelectAnalysisContentService,
)
from mrinsight.papers.repositories import PaperChunkRepository, PaperRepository
from mrinsight.relevance import (
    RELEVANCE_MODEL_VERSION,
    RELEVANCE_RULES_VERSION,
    NewRelevanceAssessment,
    RelevanceAssessmentServiceResult,
    RuleBasedRelevanceScorer,
)
from mrinsight.relevance.repositories import RelevanceAssessmentRepository


@dataclass(frozen=True, slots=True)
class AssessPaperRelevanceService:
    """Compute or retrieve deterministic relevance for one paper."""

    paper_repository: PaperRepository
    content_selector: SelectAnalysisContentService
    chunk_repository: PaperChunkRepository
    assessment_repository: RelevanceAssessmentRepository
    scorer: RuleBasedRelevanceScorer

    def execute(
        self,
        paper_id: int,
    ) -> RelevanceAssessmentServiceResult:
        """Compute or retrieve the current relevance assessment."""

        paper = self.paper_repository.get_by_id(paper_id)

        if paper is None:
            raise PaperNotFoundError(f"Paper {paper_id} does not exist.")

        selected = self.content_selector.execute(paper_id)

        if selected.content.checksum is None or selected.content.extracted_text is None:
            raise NoAnalyzableContentError(
                f"Paper {paper_id} has no successful extracted text."
            )

        cached = self.assessment_repository.get_current(
            paper_id=paper.id,
            paper_content_id=selected.content.id,
            analysis_scope=selected.scope,
            content_checksum=selected.content.checksum,
            rule_version=RELEVANCE_RULES_VERSION,
            ontology_version=self.scorer.ontology_version,
            model_version=RELEVANCE_MODEL_VERSION,
        )

        if cached is not None:
            return RelevanceAssessmentServiceResult(
                assessment=cached,
                cached=True,
            )

        chunks = self.chunk_repository.list_by_content(selected.content.id)
        score = self.scorer.score(
            paper=paper,
            selected_text=selected.content.extracted_text,
            chunks=chunks,
        )

        stored = self.assessment_repository.add(
            NewRelevanceAssessment(
                paper_id=paper.id,
                paper_content_id=selected.content.id,
                analysis_scope=selected.scope,
                content_checksum=selected.content.checksum,
                rule_score=score.total_score,
                normalized_score=score.normalized_score,
                rule_label=score.label,
                category_scores=score.category_scores,
                matched_concepts=score.matched_concepts,
                matched_terms=tuple(match.to_json() for match in score.matched_terms),
                supporting_locations=tuple(
                    location.to_json() for location in score.supporting_locations
                ),
                rule_version=score.rules_version,
                ontology_version=score.ontology_version,
                model_version=RELEVANCE_MODEL_VERSION,
                explanation=score.explanation,
            )
        )

        return RelevanceAssessmentServiceResult(
            assessment=stored,
            cached=False,
        )
