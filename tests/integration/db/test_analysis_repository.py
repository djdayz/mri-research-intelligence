from datetime import UTC, datetime

import pytest
from sqlalchemy.orm import Session

from mrinsight.analysis import ANALYSIS_SCHEMA_VERSION
from mrinsight.analysis.records import (
    LLMRunStatus,
    NewLLMRun,
    NewPaperAnalysis,
    PaperAnalysisStatus,
)
from mrinsight.db.models import Paper, PaperContent
from mrinsight.db.repositories import (
    SqlAlchemyLLMRunRepository,
    SqlAlchemyPaperAnalysisRepository,
)
from mrinsight.nlp import TEXT_CLEANER_VERSION, compute_text_checksum
from mrinsight.papers import AnalysisScope, ContentType, ExtractionStatus


def create_parent_content(
    session: Session,
) -> tuple[Paper, PaperContent]:
    """Insert one paper and successful content record."""

    paper = Paper(
        doi="10.1234/analysis.repository",
        normalized_doi="10.1234/analysis.repository",
        title="BOLD CVR MRI analysis",
        normalized_title="bold cvr mri analysis",
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
def test_repositories_persist_llm_run_and_successful_analysis(
    db_session: Session,
) -> None:
    paper, content = create_parent_content(db_session)
    run_repository = SqlAlchemyLLMRunRepository(db_session)
    analysis_repository = SqlAlchemyPaperAnalysisRepository(db_session)

    run = run_repository.add(
        NewLLMRun(
            provider="fake",
            model="fake-analysis-model-v1",
            prompt_version="analysis-prompt-v1",
            prompt_checksum="a" * 64,
            schema_version=ANALYSIS_SCHEMA_VERSION,
            input_checksum="b" * 64,
            selected_chunk_ids=(1, 2),
            request_status=LLMRunStatus.SUCCEEDED,
            repair_attempt_count=1,
            provider_request_id="fake-1",
            input_token_count=10,
            output_token_count=20,
            latency_ms=30,
            completed_at=datetime.now(UTC),
        )
    )
    stored = analysis_repository.add(
        NewPaperAnalysis(
            paper_id=paper.id,
            paper_content_id=content.id,
            analysis_scope=AnalysisScope.ABSTRACT_ONLY,
            content_checksum=content.checksum or "",
            selected_evidence_checksum="c" * 64,
            llm_run_id=run.id,
            schema_version=ANALYSIS_SCHEMA_VERSION,
            provider="fake",
            model="fake-analysis-model-v1",
            prompt_version="analysis-prompt-v1",
            validated_analysis={"schema_version": ANALYSIS_SCHEMA_VERSION},
            status=PaperAnalysisStatus.SUCCEEDED,
            validation_errors=(),
            relevance_version="deterministic-relevance-v1",
        )
    )

    current = analysis_repository.get_current(
        paper_id=paper.id,
        paper_content_id=content.id,
        analysis_scope=AnalysisScope.ABSTRACT_ONLY,
        content_checksum=content.checksum or "",
        selected_evidence_checksum="c" * 64,
        schema_version=ANALYSIS_SCHEMA_VERSION,
        provider="fake",
        model="fake-analysis-model-v1",
        prompt_version="analysis-prompt-v1",
    )

    assert run.selected_chunk_ids == (1, 2)
    assert stored.llm_run_id == run.id
    assert current is not None
    assert current.cached is True
    assert current.validated_analysis == {"schema_version": ANALYSIS_SCHEMA_VERSION}


@pytest.mark.integration
def test_failed_analysis_is_not_returned_as_current_cache(
    db_session: Session,
) -> None:
    paper, content = create_parent_content(db_session)
    analysis_repository = SqlAlchemyPaperAnalysisRepository(db_session)

    analysis_repository.add(
        NewPaperAnalysis(
            paper_id=paper.id,
            paper_content_id=content.id,
            analysis_scope=AnalysisScope.ABSTRACT_ONLY,
            content_checksum=content.checksum or "",
            selected_evidence_checksum="d" * 64,
            llm_run_id=None,
            schema_version=ANALYSIS_SCHEMA_VERSION,
            provider="openai",
            model="gpt-test",
            prompt_version="analysis-prompt-v1",
            validated_analysis=None,
            status=PaperAnalysisStatus.FAILED,
            validation_errors=("provider failed",),
            relevance_version="deterministic-relevance-v1",
        )
    )

    current = analysis_repository.get_current(
        paper_id=paper.id,
        paper_content_id=content.id,
        analysis_scope=AnalysisScope.ABSTRACT_ONLY,
        content_checksum=content.checksum or "",
        selected_evidence_checksum="d" * 64,
        schema_version=ANALYSIS_SCHEMA_VERSION,
        provider="openai",
        model="gpt-test",
        prompt_version="analysis-prompt-v1",
    )

    assert current is None
