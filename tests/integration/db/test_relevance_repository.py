from datetime import UTC, datetime

import pytest
from sqlalchemy.orm import Session

from mrinsight.db.models import Paper, PaperContent
from mrinsight.db.repositories import SqlAlchemyRelevanceAssessmentRepository
from mrinsight.nlp import TEXT_CLEANER_VERSION, compute_text_checksum
from mrinsight.papers import AnalysisScope, ContentType, ExtractionStatus
from mrinsight.relevance import NewRelevanceAssessment, RelevanceLabel


def create_parent_content(
    session: Session,
) -> tuple[Paper, PaperContent]:
    """Insert one paper and successful abstract content record."""

    paper = Paper(
        doi="10.1234/relevance.repository",
        normalized_doi="10.1234/relevance.repository",
        title="BOLD CVR MRI",
        normalized_title="bold cvr mri",
        abstract="Cerebrovascular reactivity with MRI.",
        ingestion_source="test",
    )
    session.add(paper)
    session.flush()

    text = "Cerebrovascular reactivity with MRI."
    content = PaperContent(
        paper_id=paper.id,
        content_type=ContentType.ABSTRACT.value,
        extraction_status=ExtractionStatus.SUCCEEDED.value,
        extracted_text=text,
        parser_version=TEXT_CLEANER_VERSION,
        checksum=compute_text_checksum(text),
    )
    session.add(content)
    session.flush()

    return paper, content


@pytest.mark.integration
def test_repository_adds_and_retrieves_current_assessment(
    db_session: Session,
) -> None:
    paper, content = create_parent_content(db_session)
    repository = SqlAlchemyRelevanceAssessmentRepository(db_session)

    stored = repository.add(
        NewRelevanceAssessment(
            paper_id=paper.id,
            paper_content_id=content.id,
            analysis_scope=AnalysisScope.ABSTRACT_ONLY,
            content_checksum=content.checksum or "",
            rule_score=90.0,
            normalized_score=1.0,
            rule_label=RelevanceLabel.HIGH,
            category_scores={"mri": 20.0, "cvr": 40.0},
            matched_concepts=("cvr", "mri_general"),
            matched_terms=({"concept_id": "cvr"},),
            supporting_locations=({"source": "title"},),
            rule_version="rules-v1",
            ontology_version="ontology-v1",
            model_version="model-v1",
            explanation="Strong CVR and MRI evidence.",
        )
    )

    retrieved = repository.get_current(
        paper_id=paper.id,
        paper_content_id=content.id,
        analysis_scope=AnalysisScope.ABSTRACT_ONLY,
        content_checksum=content.checksum or "",
        rule_version="rules-v1",
        ontology_version="ontology-v1",
        model_version="model-v1",
    )

    assert retrieved == stored
    assert retrieved is not None
    assert retrieved.created_at <= datetime.now(tz=UTC)
