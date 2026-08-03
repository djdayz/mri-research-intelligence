from collections.abc import Iterator
from functools import lru_cache
from pathlib import Path
from typing import Annotated

import httpx
from fastapi import Depends
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from mrinsight.analysis import (
    AnalysisEvidenceValidator,
    EvidenceSelectionService,
    FakeLLMProvider,
    GeneratePaperAnalysisService,
    LLMProvider,
    OpenAIResponsesLLMProvider,
    UnconfiguredLLMProvider,
)
from mrinsight.analysis.repositories import (
    LLMRunRepository,
    PaperAnalysisRepository,
)
from mrinsight.application.services import (
    AnalyzePaperService,
    AssessPaperRelevanceService,
    BuildPaperChunksService,
    CreateSubscriptionService,
    IngestFullTextService,
    IngestPaperService,
    RunDigestPreviewService,
    SelectAnalysisContentService,
    StoreAbstractContentService,
)
from mrinsight.core.config import get_settings
from mrinsight.db.repositories import (
    SqlAlchemyDiscoveryRepository,
    SqlAlchemyLLMRunRepository,
    SqlAlchemyPaperAnalysisRepository,
    SqlAlchemyPaperChunkRepository,
    SqlAlchemyPaperContentPageRepository,
    SqlAlchemyPaperContentRepository,
    SqlAlchemyPaperRepository,
    SqlAlchemyPaperRetrievalRepository,
    SqlAlchemyRelevanceAssessmentRepository,
)
from mrinsight.db.session import (
    create_pooled_database_engine,
    create_session_factory,
)
from mrinsight.discovery import (
    ConsoleDigestDeliveryProvider,
    CrossrefDiscoveryProvider,
    DigestDeliveryProvider,
    DiscoveryProvider,
    DiscoveryRepository,
    FakeDiscoveryProvider,
    FileDigestDeliveryProvider,
    SmtpDigestDeliveryConfig,
    SmtpDigestDeliveryProvider,
)
from mrinsight.documents import PdfUploadPolicy
from mrinsight.documents.extractors import (
    PdfDocumentInspector,
    PdfTextExtractor,
    PypdfDocumentAdapter,
)
from mrinsight.papers.providers import (
    BibliographicProvider,
    CrossrefBibliographicProvider,
    UnconfiguredBibliographicProvider,
)
from mrinsight.papers.repositories import (
    PaperChunkRepository,
    PaperContentPageRepository,
    PaperContentRepository,
    PaperRepository,
)
from mrinsight.relevance import RuleBasedRelevanceScorer
from mrinsight.relevance.repositories import RelevanceAssessmentRepository
from mrinsight.retrieval import PaperRetrievalRepository


@lru_cache
def get_database_engine() -> Engine:
    """Return the process-wide SQLAlchemy engine."""

    settings = get_settings()

    return create_pooled_database_engine(
        settings.database_url,
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
        pool_timeout_seconds=settings.database_pool_timeout_seconds,
        pool_recycle_seconds=settings.database_pool_recycle_seconds,
    )


@lru_cache
def get_database_session_factory() -> sessionmaker[Session]:
    """Return the process-wide database session factory."""

    return create_session_factory(get_database_engine())


def get_db_session() -> Iterator[Session]:
    """Provide one transaction-scoped database session."""

    session_factory = get_database_session_factory()

    with session_factory() as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise


@lru_cache
def get_bibliographic_provider() -> BibliographicProvider:
    """Return the configured bibliographic provider."""

    settings = get_settings()

    if not settings.crossref_mailto:
        return UnconfiguredBibliographicProvider()

    return CrossrefBibliographicProvider(
        client=get_http_client(),
        mailto=settings.crossref_mailto,
        user_agent=settings.crossref_user_agent,
        base_url=settings.crossref_base_url,
        max_attempts=settings.crossref_max_attempts,
        backoff_seconds=(settings.crossref_backoff_seconds),
    )


def get_paper_repository(
    session: Annotated[
        Session,
        Depends(get_db_session),
    ],
) -> PaperRepository:
    """Construct the SQLAlchemy paper repository."""

    return SqlAlchemyPaperRepository(session)


def get_paper_content_repository(
    session: Annotated[
        Session,
        Depends(get_db_session),
    ],
) -> PaperContentRepository:
    """Construct the SQLAlchemy paper-content repository."""

    return SqlAlchemyPaperContentRepository(session)


def get_paper_content_page_repository(
    session: Annotated[
        Session,
        Depends(get_db_session),
    ],
) -> PaperContentPageRepository:
    """Construct the SQLAlchemy content-page repository."""

    return SqlAlchemyPaperContentPageRepository(session)


def get_store_abstract_content_service(
    repository: Annotated[
        PaperContentRepository,
        Depends(get_paper_content_repository),
    ],
) -> StoreAbstractContentService:
    """Construct the abstract-content storage service."""

    return StoreAbstractContentService(repository)


def get_select_analysis_content_service(
    repository: Annotated[
        PaperContentRepository,
        Depends(get_paper_content_repository),
    ],
) -> SelectAnalysisContentService:
    """Construct the analysis-content selector."""

    return SelectAnalysisContentService(repository)


def get_paper_chunk_repository(
    session: Annotated[
        Session,
        Depends(get_db_session),
    ],
) -> PaperChunkRepository:
    """Construct the SQLAlchemy chunk repository."""

    return SqlAlchemyPaperChunkRepository(session)


def get_relevance_assessment_repository(
    session: Annotated[
        Session,
        Depends(get_db_session),
    ],
) -> RelevanceAssessmentRepository:
    """Construct the SQLAlchemy relevance-assessment repository."""

    return SqlAlchemyRelevanceAssessmentRepository(session)


def get_paper_retrieval_repository(
    session: Annotated[
        Session,
        Depends(get_db_session),
    ],
) -> PaperRetrievalRepository:
    """Construct the SQLAlchemy paper-retrieval repository."""

    return SqlAlchemyPaperRetrievalRepository(session)


def get_discovery_repository(
    session: Annotated[
        Session,
        Depends(get_db_session),
    ],
) -> DiscoveryRepository:
    """Construct the SQLAlchemy discovery repository."""

    return SqlAlchemyDiscoveryRepository(session)


def get_llm_run_repository(
    session: Annotated[
        Session,
        Depends(get_db_session),
    ],
) -> LLMRunRepository:
    """Construct the SQLAlchemy LLM-run repository."""

    return SqlAlchemyLLMRunRepository(session)


def get_paper_analysis_repository(
    session: Annotated[
        Session,
        Depends(get_db_session),
    ],
) -> PaperAnalysisRepository:
    """Construct the SQLAlchemy paper-analysis repository."""

    return SqlAlchemyPaperAnalysisRepository(session)


@lru_cache
def get_discovery_provider() -> DiscoveryProvider:
    """Return the configured discovery provider."""

    settings = get_settings()

    if settings.crossref_mailto:
        return CrossrefDiscoveryProvider(
            client=get_http_client(),
            mailto=settings.crossref_mailto,
            user_agent=settings.crossref_user_agent,
            base_url=settings.crossref_base_url,
            max_attempts=settings.crossref_max_attempts,
            backoff_seconds=settings.crossref_backoff_seconds,
        )

    return FakeDiscoveryProvider(())


@lru_cache
def get_digest_delivery_provider() -> DigestDeliveryProvider:
    """Return the configured digest preview delivery provider."""

    settings = get_settings()

    if settings.digest_delivery_provider == "console":
        return ConsoleDigestDeliveryProvider()

    if settings.digest_delivery_provider == "smtp":
        if settings.smtp_host is None or settings.smtp_sender is None:
            raise RuntimeError(
                "SMTP delivery requires MRINSIGHT_SMTP_HOST and MRINSIGHT_SMTP_SENDER."
            )
        return SmtpDigestDeliveryProvider(
            SmtpDigestDeliveryConfig(
                host=settings.smtp_host,
                port=settings.smtp_port,
                sender=settings.smtp_sender,
                username=settings.smtp_username,
                password=settings.smtp_password,
                use_tls=settings.smtp_use_tls,
                use_ssl=settings.smtp_use_ssl,
                timeout_seconds=settings.smtp_timeout_seconds,
                max_attempts=settings.smtp_max_attempts,
                backoff_seconds=settings.smtp_backoff_seconds,
            )
        )

    return FileDigestDeliveryProvider(Path("var/digests"))


def get_create_subscription_service(
    repository: Annotated[
        DiscoveryRepository,
        Depends(get_discovery_repository),
    ],
) -> CreateSubscriptionService:
    """Construct subscription creation service."""

    return CreateSubscriptionService(repository)


@lru_cache
def get_rule_based_relevance_scorer() -> RuleBasedRelevanceScorer:
    """Return the process-wide deterministic relevance scorer."""

    return RuleBasedRelevanceScorer()


def get_build_paper_chunks_service(
    repository: Annotated[
        PaperChunkRepository,
        Depends(get_paper_chunk_repository),
    ],
) -> BuildPaperChunksService:
    """Construct the chunk-building service."""

    return BuildPaperChunksService(repository)


@lru_cache
def get_pdf_document_adapter() -> PypdfDocumentAdapter:
    """Return the process-wide PDF adapter."""

    return PypdfDocumentAdapter()


def get_pdf_inspector(
    adapter: Annotated[
        PypdfDocumentAdapter,
        Depends(get_pdf_document_adapter),
    ],
) -> PdfDocumentInspector:
    """Return the PDF document inspector."""

    return adapter


def get_pdf_text_extractor(
    adapter: Annotated[
        PypdfDocumentAdapter,
        Depends(get_pdf_document_adapter),
    ],
) -> PdfTextExtractor:
    """Return the PDF text extractor."""

    return adapter


def get_pdf_upload_policy() -> PdfUploadPolicy:
    """Return the configured PDF upload policy."""

    settings = get_settings()

    return PdfUploadPolicy(
        max_bytes=settings.pdf_max_bytes,
        max_pages=settings.pdf_max_pages,
    )


def get_ingest_full_text_service(
    paper_repository: Annotated[
        PaperRepository,
        Depends(get_paper_repository),
    ],
    content_repository: Annotated[
        PaperContentRepository,
        Depends(get_paper_content_repository),
    ],
    page_repository: Annotated[
        PaperContentPageRepository,
        Depends(get_paper_content_page_repository),
    ],
    chunk_service: Annotated[
        BuildPaperChunksService,
        Depends(get_build_paper_chunks_service),
    ],
    inspector: Annotated[
        PdfDocumentInspector,
        Depends(get_pdf_inspector),
    ],
    extractor: Annotated[
        PdfTextExtractor,
        Depends(get_pdf_text_extractor),
    ],
    policy: Annotated[
        PdfUploadPolicy,
        Depends(get_pdf_upload_policy),
    ],
) -> IngestFullTextService:
    """Construct the full-text ingestion service."""

    return IngestFullTextService(
        paper_repository=paper_repository,
        content_repository=content_repository,
        page_repository=page_repository,
        chunk_service=chunk_service,
        inspector=inspector,
        extractor=extractor,
        policy=policy,
    )


def get_ingest_paper_service(
    provider: Annotated[
        BibliographicProvider,
        Depends(get_bibliographic_provider),
    ],
    repository: Annotated[
        PaperRepository,
        Depends(get_paper_repository),
    ],
    abstract_content_service: Annotated[
        StoreAbstractContentService,
        Depends(get_store_abstract_content_service),
    ],
    chunk_service: Annotated[
        BuildPaperChunksService,
        Depends(get_build_paper_chunks_service),
    ],
) -> IngestPaperService:
    """Construct the DOI-ingestion application service."""

    return IngestPaperService(
        provider=provider,
        repository=repository,
        abstract_content_service=(abstract_content_service),
        chunk_service=chunk_service,
    )


def get_assess_paper_relevance_service(
    paper_repository: Annotated[
        PaperRepository,
        Depends(get_paper_repository),
    ],
    content_selector: Annotated[
        SelectAnalysisContentService,
        Depends(get_select_analysis_content_service),
    ],
    chunk_repository: Annotated[
        PaperChunkRepository,
        Depends(get_paper_chunk_repository),
    ],
    assessment_repository: Annotated[
        RelevanceAssessmentRepository,
        Depends(get_relevance_assessment_repository),
    ],
    scorer: Annotated[
        RuleBasedRelevanceScorer,
        Depends(get_rule_based_relevance_scorer),
    ],
) -> AssessPaperRelevanceService:
    """Construct the relevance assessment service."""

    return AssessPaperRelevanceService(
        paper_repository=paper_repository,
        content_selector=content_selector,
        chunk_repository=chunk_repository,
        assessment_repository=assessment_repository,
        scorer=scorer,
    )


@lru_cache
def get_analysis_evidence_validator() -> AnalysisEvidenceValidator:
    """Return the process-wide analysis evidence validator."""

    return AnalysisEvidenceValidator()


@lru_cache
def get_llm_provider() -> LLMProvider:
    """Return the configured LLM provider."""

    settings = get_settings()

    if settings.llm_provider == "fake":
        return FakeLLMProvider(model_identifier=settings.llm_model)

    if settings.llm_provider == "openai" and settings.llm_api_key:
        return OpenAIResponsesLLMProvider(
            api_key=settings.llm_api_key,
            model_identifier=settings.llm_model,
            timeout_seconds=settings.llm_timeout_seconds,
            max_retries=settings.llm_max_retries,
        )

    return UnconfiguredLLMProvider()


def get_evidence_selection_service() -> EvidenceSelectionService:
    """Construct the deterministic evidence selector."""

    settings = get_settings()

    return EvidenceSelectionService(
        max_prompt_tokens=settings.llm_prompt_budget_tokens,
    )


def get_generate_paper_analysis_service(
    provider: Annotated[
        LLMProvider,
        Depends(get_llm_provider),
    ],
    validator: Annotated[
        AnalysisEvidenceValidator,
        Depends(get_analysis_evidence_validator),
    ],
) -> GeneratePaperAnalysisService:
    """Construct the structured analysis generator."""

    settings = get_settings()

    return GeneratePaperAnalysisService(
        provider=provider,
        validator=validator,
        model_identifier=settings.llm_model,
    )


def get_analyze_paper_service(
    paper_repository: Annotated[
        PaperRepository,
        Depends(get_paper_repository),
    ],
    content_selector: Annotated[
        SelectAnalysisContentService,
        Depends(get_select_analysis_content_service),
    ],
    chunk_repository: Annotated[
        PaperChunkRepository,
        Depends(get_paper_chunk_repository),
    ],
    analysis_repository: Annotated[
        PaperAnalysisRepository,
        Depends(get_paper_analysis_repository),
    ],
    llm_run_repository: Annotated[
        LLMRunRepository,
        Depends(get_llm_run_repository),
    ],
    evidence_selector: Annotated[
        EvidenceSelectionService,
        Depends(get_evidence_selection_service),
    ],
    generation_service: Annotated[
        GeneratePaperAnalysisService,
        Depends(get_generate_paper_analysis_service),
    ],
    provider: Annotated[
        LLMProvider,
        Depends(get_llm_provider),
    ],
) -> AnalyzePaperService:
    """Construct the paper-analysis orchestration service."""

    settings = get_settings()

    return AnalyzePaperService(
        paper_repository=paper_repository,
        content_selector=content_selector,
        chunk_repository=chunk_repository,
        analysis_repository=analysis_repository,
        llm_run_repository=llm_run_repository,
        evidence_selector=evidence_selector,
        generation_service=generation_service,
        provider_name=provider.name,
        model_identifier=settings.llm_model,
    )


def get_run_digest_preview_service(
    discovery_repository: Annotated[
        DiscoveryRepository,
        Depends(get_discovery_repository),
    ],
    abstract_content_service: Annotated[
        StoreAbstractContentService,
        Depends(get_store_abstract_content_service),
    ],
    chunk_service: Annotated[
        BuildPaperChunksService,
        Depends(get_build_paper_chunks_service),
    ],
    relevance_service: Annotated[
        AssessPaperRelevanceService,
        Depends(get_assess_paper_relevance_service),
    ],
    discovery_provider: Annotated[
        DiscoveryProvider,
        Depends(get_discovery_provider),
    ],
    delivery_provider: Annotated[
        DigestDeliveryProvider,
        Depends(get_digest_delivery_provider),
    ],
) -> RunDigestPreviewService:
    """Construct digest preview workflow service."""

    settings = get_settings()

    return RunDigestPreviewService(
        discovery_repository=discovery_repository,
        abstract_content_service=abstract_content_service,
        chunk_service=chunk_service,
        relevance_service=relevance_service,
        discovery_provider=discovery_provider,
        delivery_provider=delivery_provider,
        delivery_retry_delay_seconds=settings.digest_delivery_retry_delay_seconds,
    )


@lru_cache
def get_http_client() -> httpx.Client:
    """Return the process-wide outbound HTTP client."""

    settings = get_settings()

    timeout = httpx.Timeout(
        settings.crossref_timeout_seconds,
        connect=(settings.crossref_connect_timeout_seconds),
    )

    return httpx.Client(
        timeout=timeout,
        follow_redirects=True,
    )


def close_application_resources() -> None:
    """Close process-wide database and HTTP resources."""

    get_bibliographic_provider.cache_clear()
    get_analysis_evidence_validator.cache_clear()
    get_digest_delivery_provider.cache_clear()
    get_discovery_provider.cache_clear()
    get_llm_provider.cache_clear()
    get_pdf_document_adapter.cache_clear()
    get_rule_based_relevance_scorer.cache_clear()

    if get_http_client.cache_info().currsize:
        get_http_client().close()
        get_http_client.cache_clear()

    get_database_session_factory.cache_clear()

    if get_database_engine.cache_info().currsize:
        get_database_engine().dispose()
        get_database_engine.cache_clear()
