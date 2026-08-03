from datetime import UTC, date, datetime

import pytest
from sqlalchemy.orm import Session

from mrinsight.analysis import ANALYSIS_SCHEMA_VERSION
from mrinsight.analysis.records import NewPaperAnalysis, PaperAnalysisStatus
from mrinsight.db.models import Paper, PaperContent
from mrinsight.db.repositories import (
    SqlAlchemyDiscoveryRepository,
    SqlAlchemyPaperAnalysisRepository,
    SqlAlchemyPaperChunkRepository,
    SqlAlchemyPaperContentRepository,
    SqlAlchemyPaperRepository,
    SqlAlchemyRelevanceAssessmentRepository,
)
from mrinsight.discovery import (
    DeliveryStatus,
    DigestCadence,
    DigestPaper,
    DigestStatus,
    NewSubscription,
)
from mrinsight.nlp import TEXT_CLEANER_VERSION, compute_text_checksum
from mrinsight.papers import (
    AnalysisScope,
    ContentType,
    ExtractionStatus,
    NewPaper,
    NewPaperChunk,
    NewPaperContent,
    SectionType,
)
from mrinsight.relevance import NewRelevanceAssessment, RelevanceLabel


def _new_paper(
    *,
    doi: str,
) -> NewPaper:
    return NewPaper(
        doi=doi,
        normalized_doi=doi.casefold(),
        title="Concurrent MRI paper",
        normalized_title="concurrent mri paper",
        abstract="MRI and CVR evidence.",
        journal="Journal",
        publication_date=date(2026, 1, 2),
        source_url="https://example.org/concurrent",
        ingestion_source="test",
        provider_record_id=doi,
    )


def _parent_content(
    session: Session,
    *,
    doi: str = "10.1234/conflict.parent",
) -> tuple[Paper, PaperContent]:
    paper = Paper(
        doi=doi,
        normalized_doi=doi,
        title="Conflict parent",
        normalized_title="conflict parent",
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


def _new_content(
    *,
    paper_id: int,
    text: str = "Cerebrovascular reactivity with MRI.",
) -> NewPaperContent:
    return NewPaperContent(
        paper_id=paper_id,
        content_type=ContentType.ABSTRACT,
        extraction_status=ExtractionStatus.SUCCEEDED,
        extracted_text=text,
        parser_version=TEXT_CLEANER_VERSION,
        checksum=compute_text_checksum(text),
    )


def _new_chunk(
    *,
    paper_id: int,
    content_id: int,
) -> NewPaperChunk:
    return NewPaperChunk(
        paper_id=paper_id,
        paper_content_id=content_id,
        section_type=SectionType.ABSTRACT,
        heading=None,
        sequence_number=1,
        text="Cerebrovascular reactivity with MRI.",
        start_char=0,
        end_char=36,
        paragraph_start_sequence=1,
        paragraph_end_sequence=1,
        token_count=5,
        page_number=None,
        chunker_version="test-chunker-v1",
    )


def _new_relevance(
    *,
    paper_id: int,
    content_id: int,
    checksum: str,
) -> NewRelevanceAssessment:
    return NewRelevanceAssessment(
        paper_id=paper_id,
        paper_content_id=content_id,
        analysis_scope=AnalysisScope.ABSTRACT_ONLY,
        content_checksum=checksum,
        rule_score=90.0,
        normalized_score=0.9,
        rule_label=RelevanceLabel.HIGH,
        category_scores={"mri": 20.0, "cvr": 40.0},
        matched_concepts=("mri_general", "cvr"),
        matched_terms=({"concept_id": "cvr"},),
        supporting_locations=({"source": "abstract"},),
        rule_version="rules-v1",
        ontology_version="ontology-v1",
        model_version="model-v1",
        explanation="Strong MRI and CVR evidence.",
    )


def _new_analysis(
    *,
    paper_id: int,
    content_id: int,
    checksum: str,
    selected_checksum: str = "a" * 64,
) -> NewPaperAnalysis:
    return NewPaperAnalysis(
        paper_id=paper_id,
        paper_content_id=content_id,
        analysis_scope=AnalysisScope.ABSTRACT_ONLY,
        content_checksum=checksum,
        selected_evidence_checksum=selected_checksum,
        llm_run_id=None,
        schema_version=ANALYSIS_SCHEMA_VERSION,
        provider="fake",
        model="fake-analysis-model-v1",
        prompt_version="analysis-prompt-v1",
        validated_analysis={"schema_version": ANALYSIS_SCHEMA_VERSION},
        status=PaperAnalysisStatus.SUCCEEDED,
        validation_errors=(),
        relevance_version="deterministic-relevance-v1",
    )


@pytest.mark.integration
def test_duplicate_paper_insert_recovers_existing_row(
    db_session: Session,
) -> None:
    repository = SqlAlchemyPaperRepository(db_session)

    created = repository.add(_new_paper(doi="10.1234/conflict.paper"))
    recovered = repository.add(_new_paper(doi="10.1234/conflict.paper"))

    assert recovered.id == created.id


@pytest.mark.integration
def test_duplicate_content_insert_recovers_existing_row(
    db_session: Session,
) -> None:
    paper = SqlAlchemyPaperRepository(db_session).add(
        _new_paper(doi="10.1234/conflict.content")
    )
    repository = SqlAlchemyPaperContentRepository(db_session)

    created = repository.add(_new_content(paper_id=paper.id))
    recovered = repository.add(_new_content(paper_id=paper.id))

    assert recovered.id == created.id


@pytest.mark.integration
def test_duplicate_chunk_insert_recovers_existing_sequence(
    db_session: Session,
) -> None:
    paper, content = _parent_content(db_session, doi="10.1234/conflict.chunk")
    repository = SqlAlchemyPaperChunkRepository(db_session)

    created = repository.add_many(
        (_new_chunk(paper_id=paper.id, content_id=content.id),)
    )
    recovered = repository.add_many(
        (_new_chunk(paper_id=paper.id, content_id=content.id),)
    )

    assert tuple(chunk.id for chunk in recovered) == tuple(
        chunk.id for chunk in created
    )


@pytest.mark.integration
def test_duplicate_relevance_insert_recovers_existing_assessment(
    db_session: Session,
) -> None:
    paper, content = _parent_content(db_session, doi="10.1234/conflict.relevance")
    repository = SqlAlchemyRelevanceAssessmentRepository(db_session)
    checksum = content.checksum or ""

    created = repository.add(
        _new_relevance(paper_id=paper.id, content_id=content.id, checksum=checksum)
    )
    recovered = repository.add(
        _new_relevance(paper_id=paper.id, content_id=content.id, checksum=checksum)
    )

    assert recovered.id == created.id


@pytest.mark.integration
def test_duplicate_successful_analysis_insert_recovers_existing_analysis(
    db_session: Session,
) -> None:
    paper, content = _parent_content(db_session, doi="10.1234/conflict.analysis")
    repository = SqlAlchemyPaperAnalysisRepository(db_session)
    checksum = content.checksum or ""

    created = repository.add(
        _new_analysis(paper_id=paper.id, content_id=content.id, checksum=checksum)
    )
    recovered = repository.add(
        _new_analysis(paper_id=paper.id, content_id=content.id, checksum=checksum)
    )

    assert recovered.id == created.id
    assert recovered.cached is True


@pytest.mark.integration
def test_failed_analysis_insert_remains_retryable(
    db_session: Session,
) -> None:
    paper, content = _parent_content(
        db_session,
        doi="10.1234/conflict.failed.analysis",
    )
    repository = SqlAlchemyPaperAnalysisRepository(db_session)
    checksum = content.checksum or ""
    analysis = _new_analysis(
        paper_id=paper.id,
        content_id=content.id,
        checksum=checksum,
        selected_checksum="b" * 64,
    )
    failed = NewPaperAnalysis(
        paper_id=analysis.paper_id,
        paper_content_id=analysis.paper_content_id,
        analysis_scope=analysis.analysis_scope,
        content_checksum=analysis.content_checksum,
        selected_evidence_checksum=analysis.selected_evidence_checksum,
        llm_run_id=analysis.llm_run_id,
        schema_version=analysis.schema_version,
        provider=analysis.provider,
        model=analysis.model,
        prompt_version=analysis.prompt_version,
        validated_analysis=None,
        status=PaperAnalysisStatus.FAILED,
        validation_errors=("provider failed",),
        relevance_version=analysis.relevance_version,
    )

    first = repository.add(failed)
    second = repository.add(failed)

    assert second.id != first.id


@pytest.mark.integration
def test_duplicate_digest_and_delivery_insert_recover_existing_rows(
    db_session: Session,
) -> None:
    repository = SqlAlchemyDiscoveryRepository(db_session)
    topic = repository.list_topics()[0]
    subscription = repository.add_subscription(
        NewSubscription(
            name=f"Conflict digest {datetime.now(UTC).isoformat()}",
            discovery_query="MRI CVR",
            topic_ids=(topic.id,),
            minimum_relevance_score=0.0,
            preferred_categories=("mri", "cvr"),
            digest_cadence=DigestCadence.WEEKLY,
        )
    )
    paper = DigestPaper(
        paper_id=1,
        doi="10.1234/conflict.digest",
        title="Conflict digest paper",
        journal="Journal",
        publication_date=date(2026, 1, 2),
        relevance_score=0.9,
        analysis_scope="abstract_only",
        concise_summary="Summary",
        methodology_highlights=("Methods",),
        main_results=("Results",),
        limitations=("Limitations",),
        link="https://doi.org/10.1234/conflict.digest",
        provenance="fake",
        ranking_explanation="score",
    )

    created_digest = repository.add_digest(
        idempotency_key="conflict-digest-key",
        subscription_id=subscription.id,
        topic_id=topic.id,
        digest_date=date(2026, 1, 31),
        period_start=date(2026, 1, 1),
        period_end=date(2026, 1, 31),
        status=DigestStatus.GENERATED,
        title="Digest",
        plain_text="Digest",
        html="<html></html>",
        selected_papers=(paper,),
        error=None,
    )
    recovered_digest = repository.add_digest(
        idempotency_key="conflict-digest-key",
        subscription_id=subscription.id,
        topic_id=topic.id,
        digest_date=date(2026, 1, 31),
        period_start=date(2026, 1, 1),
        period_end=date(2026, 1, 31),
        status=DigestStatus.GENERATED,
        title="Digest retry",
        plain_text="Digest retry",
        html="<html></html>",
        selected_papers=(paper,),
        error=None,
    )
    created_delivery = repository.add_delivery(
        digest_id=created_digest.id,
        provider="fake",
        destination=None,
        status=DeliveryStatus.SUCCEEDED,
        idempotency_key="conflict-delivery-key",
        error=None,
    )
    recovered_delivery = repository.add_delivery(
        digest_id=created_digest.id,
        provider="fake",
        destination=None,
        status=DeliveryStatus.SUCCEEDED,
        idempotency_key="conflict-delivery-key",
        error=None,
    )

    assert recovered_digest.id == created_digest.id
    assert recovered_digest.title == "Digest"
    assert recovered_delivery.id == created_delivery.id
