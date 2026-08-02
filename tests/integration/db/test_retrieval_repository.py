from datetime import date

import pytest
from sqlalchemy.orm import Session

from mrinsight.analysis import ANALYSIS_SCHEMA_VERSION
from mrinsight.db.models import (
    Paper,
    PaperAnalysis,
    PaperChunk,
    PaperContent,
    PaperRelevanceAssessment,
)
from mrinsight.db.repositories import SqlAlchemyPaperRetrievalRepository
from mrinsight.nlp import TEXT_CLEANER_VERSION, compute_text_checksum
from mrinsight.papers import AnalysisScope, ContentType, ExtractionStatus, SectionType
from mrinsight.retrieval import PageRequest, PaperSearchFilters, PaperSort


def create_search_fixture(
    session: Session,
) -> tuple[Paper, Paper, Paper]:
    """Insert a small retrieval fixture with content, relevance, and analysis."""

    first = _paper(
        doi="10.1234/first",
        title="BOLD CVR MRI",
        publication_date=date(2026, 1, 1),
        journal="Journal A",
        ingestion_source="fake",
    )
    second = _paper(
        doi="10.1234/second",
        title="Diffusion MRI Reconstruction",
        publication_date=date(2025, 1, 1),
        journal="Journal B",
        ingestion_source="crossref",
    )
    third = _paper(
        doi="10.1234/third",
        title="Cardiology Registry",
        publication_date=date(2024, 1, 1),
        journal="Journal A",
        ingestion_source="fake",
    )
    session.add_all([first, second, third])
    session.flush()

    first_content = _content(
        paper_id=first.id,
        text="Cerebrovascular reactivity with BOLD MRI.",
    )
    second_content = _content(
        paper_id=second.id,
        text="MRI reconstruction methods reported 2.5 units.",
    )
    third_content = _content(
        paper_id=third.id,
        text="Cardiology registry outcomes.",
    )
    session.add_all([first_content, second_content, third_content])
    session.flush()

    session.add_all(
        [
            _chunk(
                paper_id=first.id,
                content_id=first_content.id,
                text="Methods used BOLD MRI for CVR.",
                section=SectionType.METHODS,
                sequence_number=1,
            ),
            _chunk(
                paper_id=first.id,
                content_id=first_content.id,
                text="Results showed CVR change.",
                section=SectionType.RESULTS,
                sequence_number=2,
            ),
            _chunk(
                paper_id=second.id,
                content_id=second_content.id,
                text="MRI reconstruction results reported 2.5.",
                section=SectionType.RESULTS,
                sequence_number=1,
            ),
        ]
    )
    session.add_all(
        [
            _relevance(
                paper_id=first.id,
                content_id=first_content.id,
                label="high",
                score=0.95,
                category_scores={"mri": 20.0, "cvr": 40.0},
                matched_concepts=["mri_general", "cvr"],
            ),
            _relevance(
                paper_id=second.id,
                content_id=second_content.id,
                label="medium",
                score=0.55,
                category_scores={"mri": 20.0, "reconstruction": 30.0},
                matched_concepts=["mri_general", "mri_reconstruction"],
            ),
        ]
    )
    session.add(
        _analysis(
            paper_id=first.id,
            content_id=first_content.id,
            status="succeeded",
        )
    )
    session.flush()

    return first, second, third


@pytest.mark.integration
def test_search_papers_paginates_and_sorts_by_newest_publication(
    db_session: Session,
) -> None:
    first, second, _third = create_search_fixture(db_session)
    repository = SqlAlchemyPaperRetrievalRepository(db_session)

    result = repository.search_papers(
        filters=PaperSearchFilters(),
        page=PageRequest(limit=2, offset=0),
        sort=PaperSort.NEWEST_PUBLICATION,
    )

    assert result.total == 3
    assert [item.id for item in result.items] == [first.id, second.id]


@pytest.mark.integration
def test_search_papers_filters_by_relevance_category_and_analysis(
    db_session: Session,
) -> None:
    first, _second, _third = create_search_fixture(db_session)
    repository = SqlAlchemyPaperRetrievalRepository(db_session)

    result = repository.search_papers(
        filters=PaperSearchFilters(
            relevance_label="high",
            mri_category="cvr",
            analysis_status="succeeded",
            analysis_scope=AnalysisScope.ABSTRACT_ONLY.value,
        ),
        page=PageRequest(limit=10, offset=0),
        sort=PaperSort.RELEVANCE_SCORE,
    )

    assert [item.id for item in result.items] == [first.id]
    assert result.items[0].relevance is not None
    assert result.items[0].analyses[0].status == "succeeded"


@pytest.mark.integration
def test_search_papers_filters_by_title_doi_content_and_source(
    db_session: Session,
) -> None:
    _first, second, _third = create_search_fixture(db_session)
    repository = SqlAlchemyPaperRetrievalRepository(db_session)

    result = repository.search_papers(
        filters=PaperSearchFilters(
            doi="10.1234/second",
            title_query="diffusion mri",
            ingestion_source="crossref",
            content_scope=ContentType.ABSTRACT.value,
            extraction_status=ExtractionStatus.SUCCEEDED.value,
        ),
        page=PageRequest(limit=10, offset=0),
        sort=PaperSort.TITLE,
    )

    assert [item.id for item in result.items] == [second.id]
    assert result.items[0].contents


@pytest.mark.integration
def test_chunk_search_filters_by_section_and_paginates(
    db_session: Session,
) -> None:
    first, _second, _third = create_search_fixture(db_session)
    repository = SqlAlchemyPaperRetrievalRepository(db_session)

    result = repository.search_chunks(
        paper_id=first.id,
        content_id=None,
        section=SectionType.RESULTS.value,
        page=PageRequest(limit=1, offset=0),
    )

    assert result is not None
    assert result.total == 1
    assert result.items[0].section == SectionType.RESULTS.value
    assert "Results" in result.items[0].text


def _paper(
    *,
    doi: str,
    title: str,
    publication_date: date,
    journal: str,
    ingestion_source: str,
) -> Paper:
    return Paper(
        doi=doi,
        normalized_doi=doi,
        title=title,
        normalized_title=title.casefold(),
        abstract=f"Abstract for {title}",
        journal=journal,
        publication_date=publication_date,
        ingestion_source=ingestion_source,
    )


def _content(
    *,
    paper_id: int,
    text: str,
) -> PaperContent:
    return PaperContent(
        paper_id=paper_id,
        content_type=ContentType.ABSTRACT.value,
        extraction_status=ExtractionStatus.SUCCEEDED.value,
        extracted_text=text,
        parser_version=TEXT_CLEANER_VERSION,
        checksum=compute_text_checksum(text),
    )


def _chunk(
    *,
    paper_id: int,
    content_id: int,
    text: str,
    section: SectionType,
    sequence_number: int,
) -> PaperChunk:
    return PaperChunk(
        paper_id=paper_id,
        paper_content_id=content_id,
        section=section.value,
        heading=section.value.title(),
        sequence_number=sequence_number,
        text=text,
        start_char=0,
        end_char=len(text),
        paragraph_start_sequence=1,
        paragraph_end_sequence=1,
        token_count=len(text.split()),
        chunker_version="test",
    )


def _relevance(
    *,
    paper_id: int,
    content_id: int,
    label: str,
    score: float,
    category_scores: dict[str, float],
    matched_concepts: list[str],
) -> PaperRelevanceAssessment:
    return PaperRelevanceAssessment(
        paper_id=paper_id,
        paper_content_id=content_id,
        analysis_scope=AnalysisScope.ABSTRACT_ONLY.value,
        content_checksum="a" * 64,
        rule_score=score * 100,
        normalized_score=score,
        rule_label=label,
        category_scores=category_scores,
        matched_concepts=matched_concepts,
        matched_terms=[],
        supporting_locations=[],
        rule_version="rules-v1",
        ontology_version="ontology-v1",
        model_version="model-v1",
        explanation="test relevance",
    )


def _analysis(
    *,
    paper_id: int,
    content_id: int,
    status: str,
) -> PaperAnalysis:
    return PaperAnalysis(
        paper_id=paper_id,
        paper_content_id=content_id,
        analysis_scope=AnalysisScope.ABSTRACT_ONLY.value,
        content_checksum="b" * 64,
        selected_evidence_checksum="c" * 64,
        schema_version=ANALYSIS_SCHEMA_VERSION,
        provider="fake",
        model="fake-analysis-model-v1",
        prompt_version="analysis-prompt-v1",
        validated_analysis={"schema_version": ANALYSIS_SCHEMA_VERSION},
        status=status,
        validation_errors=[],
    )
