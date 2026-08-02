from typing import Any, cast

from sqlalchemy import select
from sqlalchemy.orm import Session

from mrinsight.analysis.records import (
    LLMRunStatus,
    NewLLMRun,
    NewPaperAnalysis,
    PaperAnalysisStatus,
    StoredLLMRun,
    StoredPaperAnalysis,
)
from mrinsight.db.models import LLMRun, PaperAnalysis
from mrinsight.papers import AnalysisScope


class SqlAlchemyLLMRunRepository:
    """Persist LLM runs using SQLAlchemy."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(
        self,
        run: NewLLMRun,
    ) -> StoredLLMRun:
        """Persist one LLM run and flush without committing."""

        model = LLMRun(
            provider=run.provider,
            model=run.model,
            prompt_version=run.prompt_version,
            prompt_checksum=run.prompt_checksum,
            schema_version=run.schema_version,
            input_checksum=run.input_checksum,
            selected_chunk_ids=list(run.selected_chunk_ids),
            request_status=run.request_status.value,
            repair_attempt_count=run.repair_attempt_count,
            provider_request_id=run.provider_request_id,
            input_token_count=run.input_token_count,
            output_token_count=run.output_token_count,
            latency_ms=run.latency_ms,
            estimated_cost=run.estimated_cost,
            error_category=run.error_category,
            completed_at=run.completed_at,
        )

        self._session.add(model)
        self._session.flush()
        self._session.refresh(model)

        return self._to_stored_run(model)

    @staticmethod
    def _to_stored_run(
        model: LLMRun,
    ) -> StoredLLMRun:
        """Translate an ORM model into an application value."""

        return StoredLLMRun(
            id=model.id,
            provider=model.provider,
            model=model.model,
            prompt_version=model.prompt_version,
            prompt_checksum=model.prompt_checksum,
            schema_version=model.schema_version,
            input_checksum=model.input_checksum,
            selected_chunk_ids=tuple(model.selected_chunk_ids),
            request_status=LLMRunStatus(model.request_status),
            repair_attempt_count=model.repair_attempt_count,
            provider_request_id=model.provider_request_id,
            input_token_count=model.input_token_count,
            output_token_count=model.output_token_count,
            latency_ms=model.latency_ms,
            estimated_cost=model.estimated_cost,
            error_category=model.error_category,
            created_at=model.created_at,
            completed_at=model.completed_at,
        )


class SqlAlchemyPaperAnalysisRepository:
    """Persist paper analyses using SQLAlchemy."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_current(
        self,
        *,
        paper_id: int,
        paper_content_id: int,
        analysis_scope: AnalysisScope,
        content_checksum: str,
        selected_evidence_checksum: str,
        schema_version: str,
        provider: str,
        model: str,
        prompt_version: str,
    ) -> StoredPaperAnalysis | None:
        """Return a cached analysis for the exact reproducibility identity."""

        statement = select(PaperAnalysis).where(
            PaperAnalysis.paper_id == paper_id,
            PaperAnalysis.paper_content_id == paper_content_id,
            PaperAnalysis.analysis_scope == analysis_scope.value,
            PaperAnalysis.content_checksum == content_checksum,
            PaperAnalysis.selected_evidence_checksum == selected_evidence_checksum,
            PaperAnalysis.schema_version == schema_version,
            PaperAnalysis.provider == provider,
            PaperAnalysis.model == model,
            PaperAnalysis.prompt_version == prompt_version,
            PaperAnalysis.status == PaperAnalysisStatus.SUCCEEDED.value,
        )
        statement = statement.order_by(
            PaperAnalysis.created_at.desc(),
            PaperAnalysis.id.desc(),
        )
        analysis_model = self._session.execute(statement).scalars().first()

        if analysis_model is None:
            return None

        return self._to_stored_analysis(analysis_model, cached=True)

    def list_by_paper(
        self,
        paper_id: int,
    ) -> tuple[StoredPaperAnalysis, ...]:
        """Return analyses for one paper ordered newest first."""

        statement = (
            select(PaperAnalysis)
            .where(PaperAnalysis.paper_id == paper_id)
            .order_by(PaperAnalysis.created_at.desc(), PaperAnalysis.id.desc())
        )
        models = self._session.execute(statement).scalars()

        return tuple(self._to_stored_analysis(model) for model in models)

    def get_by_id(
        self,
        analysis_id: int,
    ) -> StoredPaperAnalysis | None:
        """Return one analysis by identity."""

        model = self._session.get(PaperAnalysis, analysis_id)

        if model is None:
            return None

        return self._to_stored_analysis(model)

    def add(
        self,
        analysis: NewPaperAnalysis,
    ) -> StoredPaperAnalysis:
        """Persist one paper analysis and flush without committing."""

        model = PaperAnalysis(
            paper_id=analysis.paper_id,
            paper_content_id=analysis.paper_content_id,
            analysis_scope=analysis.analysis_scope.value,
            content_checksum=analysis.content_checksum,
            selected_evidence_checksum=analysis.selected_evidence_checksum,
            llm_run_id=analysis.llm_run_id,
            schema_version=analysis.schema_version,
            provider=analysis.provider,
            model=analysis.model,
            prompt_version=analysis.prompt_version,
            validated_analysis=analysis.validated_analysis,
            status=analysis.status.value,
            validation_errors=list(analysis.validation_errors),
            relevance_version=analysis.relevance_version,
        )

        self._session.add(model)
        self._session.flush()
        self._session.refresh(model)

        return self._to_stored_analysis(model)

    @staticmethod
    def _to_stored_analysis(
        model: PaperAnalysis,
        *,
        cached: bool = False,
    ) -> StoredPaperAnalysis:
        """Translate an ORM model into an application value."""

        return StoredPaperAnalysis(
            id=model.id,
            paper_id=model.paper_id,
            paper_content_id=model.paper_content_id,
            analysis_scope=AnalysisScope(model.analysis_scope),
            content_checksum=model.content_checksum,
            selected_evidence_checksum=model.selected_evidence_checksum,
            llm_run_id=model.llm_run_id,
            schema_version=model.schema_version,
            provider=model.provider,
            model=model.model,
            prompt_version=model.prompt_version,
            validated_analysis=(
                cast(dict[str, Any], model.validated_analysis)
                if model.validated_analysis is not None
                else None
            ),
            status=PaperAnalysisStatus(model.status),
            validation_errors=tuple(model.validation_errors),
            relevance_version=model.relevance_version,
            created_at=model.created_at,
            updated_at=model.updated_at,
            cached=cached,
        )
