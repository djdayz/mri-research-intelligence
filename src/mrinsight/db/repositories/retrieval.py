from typing import Any, cast

from sqlalchemy import Select, exists, func, literal, select
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from mrinsight.db.models import (
    Paper,
    PaperAnalysis,
    PaperChunk,
    PaperContent,
    PaperRelevanceAssessment,
)
from mrinsight.retrieval.records import (
    AnalysisRetrievalSummary,
    ContentRetrievalSummary,
    PageRequest,
    PaperChunkRetrievalSummary,
    PaperChunkSearchResult,
    PaperRetrievalSummary,
    PaperSearchFilters,
    PaperSearchResult,
    PaperSort,
    RelevanceRetrievalSummary,
)


class SqlAlchemyPaperRetrievalRepository:
    """Read-only search and retrieval queries for papers."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def search_papers(
        self,
        *,
        filters: PaperSearchFilters,
        page: PageRequest,
        sort: PaperSort,
    ) -> PaperSearchResult:
        """Return one bounded page of paper summaries."""

        conditions = _paper_conditions(filters)
        total = self._count_papers(conditions)
        paper_ids = self._page_paper_ids(
            conditions=conditions,
            page=page,
            sort=sort,
        )

        return PaperSearchResult(
            items=self._summaries_for_ids(paper_ids, include_abstract=False),
            total=total,
            limit=page.limit,
            offset=page.offset,
            sort=sort,
        )

    def get_paper_detail(
        self,
        paper_id: int,
    ) -> PaperSearchResult:
        """Return one paper detail result with abstract included."""

        paper = self._session.get(Paper, paper_id)

        if paper is None:
            return PaperSearchResult(
                items=(),
                total=0,
                limit=1,
                offset=0,
                sort=PaperSort.NEWEST_INGESTION,
            )

        return PaperSearchResult(
            items=self._summaries_for_ids((paper.id,), include_abstract=True),
            total=1,
            limit=1,
            offset=0,
            sort=PaperSort.NEWEST_INGESTION,
        )

    def list_contents(
        self,
        paper_id: int,
    ) -> tuple[ContentRetrievalSummary, ...] | None:
        """Return content metadata for one paper, or None when missing."""

        if self._session.get(Paper, paper_id) is None:
            return None

        return self._contents_by_paper_ids((paper_id,)).get(paper_id, ())

    def search_chunks(
        self,
        *,
        paper_id: int,
        content_id: int | None,
        section: str | None,
        page: PageRequest,
    ) -> PaperChunkSearchResult | None:
        """Return explicit chunk text for one paper, or None when missing."""

        if self._session.get(Paper, paper_id) is None:
            return None

        conditions: list[ColumnElement[bool]] = [PaperChunk.paper_id == paper_id]
        if content_id is not None:
            conditions.append(PaperChunk.paper_content_id == content_id)
        if section is not None:
            conditions.append(PaperChunk.section == section)

        total = self._session.scalar(
            select(func.count()).select_from(PaperChunk).where(*conditions)
        )
        statement = (
            select(PaperChunk)
            .where(*conditions)
            .order_by(
                PaperChunk.paper_content_id.asc(),
                PaperChunk.sequence_number.asc(),
                PaperChunk.id.asc(),
            )
            .limit(page.limit)
            .offset(page.offset)
        )
        models = self._session.execute(statement).scalars()

        return PaperChunkSearchResult(
            items=tuple(_to_chunk_summary(model) for model in models),
            total=total or 0,
            limit=page.limit,
            offset=page.offset,
        )

    def _count_papers(
        self,
        conditions: tuple[ColumnElement[bool], ...],
    ) -> int:
        """Return count for current paper filters."""

        total = self._session.scalar(
            select(func.count()).select_from(Paper).where(*conditions)
        )

        return total or 0

    def _page_paper_ids(
        self,
        *,
        conditions: tuple[ColumnElement[bool], ...],
        page: PageRequest,
        sort: PaperSort,
    ) -> tuple[int, ...]:
        """Return ordered paper IDs for one page."""

        relevance_sort = _latest_relevance_sort_subquery()
        statement = select(Paper.id).where(*conditions)

        if sort is PaperSort.RELEVANCE_SCORE:
            statement = statement.outerjoin(
                relevance_sort,
                relevance_sort.c.paper_id == Paper.id,
            ).order_by(
                relevance_sort.c.normalized_score.desc().nulls_last(),
                Paper.id.desc(),
            )
        else:
            statement = statement.order_by(*_paper_order_by(sort))

        rows = self._session.execute(
            statement.limit(page.limit).offset(page.offset)
        ).all()

        return tuple(row[0] for row in rows)

    def _summaries_for_ids(
        self,
        paper_ids: tuple[int, ...],
        *,
        include_abstract: bool,
    ) -> tuple[PaperRetrievalSummary, ...]:
        """Return paper summaries in the requested ID order."""

        if not paper_ids:
            return ()

        papers = {
            paper.id: paper
            for paper in self._session.execute(
                select(Paper).where(Paper.id.in_(paper_ids))
            ).scalars()
        }
        contents_by_paper = self._contents_by_paper_ids(paper_ids)
        relevance_by_paper = self._latest_relevance_by_paper_ids(paper_ids)
        analyses_by_paper = self._analyses_by_paper_ids(paper_ids)

        return tuple(
            _to_paper_summary(
                papers[paper_id],
                contents=contents_by_paper.get(paper_id, ()),
                relevance=relevance_by_paper.get(paper_id),
                analyses=analyses_by_paper.get(paper_id, ()),
                include_abstract=include_abstract,
            )
            for paper_id in paper_ids
            if paper_id in papers
        )

    def _contents_by_paper_ids(
        self,
        paper_ids: tuple[int, ...],
    ) -> dict[int, tuple[ContentRetrievalSummary, ...]]:
        """Return content summaries grouped by paper ID."""

        grouped: dict[int, list[ContentRetrievalSummary]] = {}
        models = self._session.execute(
            select(PaperContent)
            .where(PaperContent.paper_id.in_(paper_ids))
            .order_by(PaperContent.paper_id.asc(), PaperContent.content_type.asc())
        ).scalars()

        for model in models:
            grouped.setdefault(model.paper_id, []).append(_to_content_summary(model))

        return {paper_id: tuple(items) for paper_id, items in grouped.items()}

    def _latest_relevance_by_paper_ids(
        self,
        paper_ids: tuple[int, ...],
    ) -> dict[int, RelevanceRetrievalSummary]:
        """Return latest relevance summary by paper ID."""

        grouped: dict[int, RelevanceRetrievalSummary] = {}
        models = self._session.execute(
            select(PaperRelevanceAssessment)
            .where(PaperRelevanceAssessment.paper_id.in_(paper_ids))
            .order_by(
                PaperRelevanceAssessment.paper_id.asc(),
                PaperRelevanceAssessment.created_at.desc(),
                PaperRelevanceAssessment.id.desc(),
            )
        ).scalars()

        for model in models:
            grouped.setdefault(model.paper_id, _to_relevance_summary(model))

        return grouped

    def _analyses_by_paper_ids(
        self,
        paper_ids: tuple[int, ...],
    ) -> dict[int, tuple[AnalysisRetrievalSummary, ...]]:
        """Return analysis summaries grouped by paper ID."""

        grouped: dict[int, list[AnalysisRetrievalSummary]] = {}
        models = self._session.execute(
            select(PaperAnalysis)
            .where(PaperAnalysis.paper_id.in_(paper_ids))
            .order_by(
                PaperAnalysis.paper_id.asc(),
                PaperAnalysis.created_at.desc(),
                PaperAnalysis.id.desc(),
            )
        ).scalars()

        for model in models:
            grouped.setdefault(model.paper_id, []).append(_to_analysis_summary(model))

        return {paper_id: tuple(items) for paper_id, items in grouped.items()}


def _paper_conditions(
    filters: PaperSearchFilters,
) -> tuple[ColumnElement[bool], ...]:
    """Build SQLAlchemy conditions for paper search filters."""

    conditions: list[ColumnElement[bool]] = []

    if filters.doi is not None:
        conditions.append(Paper.normalized_doi == filters.doi)
    if filters.title_query is not None:
        conditions.append(Paper.normalized_title.contains(filters.title_query))
    if filters.publication_date_from is not None:
        conditions.append(Paper.publication_date >= filters.publication_date_from)
    if filters.publication_date_to is not None:
        conditions.append(Paper.publication_date <= filters.publication_date_to)
    if filters.journal is not None:
        conditions.append(Paper.journal == filters.journal)
    if filters.ingestion_source is not None:
        conditions.append(Paper.ingestion_source == filters.ingestion_source)
    if filters.content_scope is not None or filters.extraction_status is not None:
        content_conditions: list[ColumnElement[bool]] = [
            PaperContent.paper_id == Paper.id
        ]
        if filters.content_scope is not None:
            content_conditions.append(
                PaperContent.content_type == filters.content_scope
            )
        if filters.extraction_status is not None:
            content_conditions.append(
                PaperContent.extraction_status == filters.extraction_status
            )
        conditions.append(exists(select(literal(1)).where(*content_conditions)))
    if filters.relevance_label is not None or filters.mri_category is not None:
        relevance_conditions: list[ColumnElement[bool]] = [
            PaperRelevanceAssessment.paper_id == Paper.id
        ]
        if filters.relevance_label is not None:
            relevance_conditions.append(
                PaperRelevanceAssessment.rule_label == filters.relevance_label
            )
        if filters.mri_category is not None:
            relevance_conditions.append(
                cast(
                    ColumnElement[bool],
                    PaperRelevanceAssessment.category_scores.op("?")(
                        filters.mri_category
                    ),
                )
            )
        conditions.append(exists(select(literal(1)).where(*relevance_conditions)))
    if filters.analysis_status is not None or filters.analysis_scope is not None:
        analysis_conditions: list[ColumnElement[bool]] = [
            PaperAnalysis.paper_id == Paper.id
        ]
        if filters.analysis_status is not None:
            analysis_conditions.append(PaperAnalysis.status == filters.analysis_status)
        if filters.analysis_scope is not None:
            analysis_conditions.append(
                PaperAnalysis.analysis_scope == filters.analysis_scope
            )
        conditions.append(exists(select(literal(1)).where(*analysis_conditions)))

    return tuple(conditions)


def _paper_order_by(
    sort: PaperSort,
) -> tuple[Any, ...]:
    """Return stable order-by expressions for a non-relevance sort."""

    if sort is PaperSort.NEWEST_PUBLICATION:
        return (
            Paper.publication_date.desc().nulls_last(),
            Paper.id.desc(),
        )
    if sort is PaperSort.OLDEST_PUBLICATION:
        return (
            Paper.publication_date.asc().nulls_last(),
            Paper.id.asc(),
        )
    if sort is PaperSort.TITLE:
        return (
            Paper.normalized_title.asc(),
            Paper.id.asc(),
        )

    return (
        Paper.created_at.desc(),
        Paper.id.desc(),
    )


def _latest_relevance_sort_subquery() -> Any:
    """Return subquery with max relevance score per paper for sorting."""

    return (
        select(
            PaperRelevanceAssessment.paper_id.label("paper_id"),
            func.max(PaperRelevanceAssessment.normalized_score).label(
                "normalized_score"
            ),
        )
        .group_by(PaperRelevanceAssessment.paper_id)
        .subquery()
    )


def _to_paper_summary(
    paper: Paper,
    *,
    contents: tuple[ContentRetrievalSummary, ...],
    relevance: RelevanceRetrievalSummary | None,
    analyses: tuple[AnalysisRetrievalSummary, ...],
    include_abstract: bool,
) -> PaperRetrievalSummary:
    """Translate a paper model into a retrieval summary."""

    return PaperRetrievalSummary(
        id=paper.id,
        doi=paper.doi,
        normalized_doi=paper.normalized_doi,
        title=paper.title,
        normalized_title=paper.normalized_title,
        abstract=paper.abstract if include_abstract else None,
        journal=paper.journal,
        publication_date=paper.publication_date,
        source_url=paper.source_url,
        ingestion_source=paper.ingestion_source,
        provider_record_id=paper.provider_record_id,
        created_at=paper.created_at,
        updated_at=paper.updated_at,
        contents=contents,
        relevance=relevance,
        analyses=analyses,
    )


def _to_content_summary(
    model: PaperContent,
) -> ContentRetrievalSummary:
    """Translate content metadata without extracted text."""

    return ContentRetrievalSummary(
        id=model.id,
        paper_id=model.paper_id,
        content_type=model.content_type,
        extraction_status=model.extraction_status,
        parser_version=model.parser_version,
        checksum=model.checksum,
        source_filename=model.source_filename,
        source_media_type=model.source_media_type,
        source_sha256=model.source_sha256,
        access_basis=model.access_basis,
        page_count=model.page_count,
        text_page_count=model.text_page_count,
        extractor_name=model.extractor_name,
        extractor_library_version=model.extractor_library_version,
        extraction_error=model.extraction_error,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _to_relevance_summary(
    model: PaperRelevanceAssessment,
) -> RelevanceRetrievalSummary:
    """Translate relevance metadata for retrieval."""

    return RelevanceRetrievalSummary(
        id=model.id,
        paper_id=model.paper_id,
        paper_content_id=model.paper_content_id,
        analysis_scope=model.analysis_scope,
        rule_label=model.rule_label,
        rule_score=model.rule_score,
        normalized_score=model.normalized_score,
        category_scores=dict(model.category_scores),
        matched_concepts=tuple(model.matched_concepts),
        rule_version=model.rule_version,
        ontology_version=model.ontology_version,
        model_version=model.model_version,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _to_analysis_summary(
    model: PaperAnalysis,
) -> AnalysisRetrievalSummary:
    """Translate analysis metadata for retrieval."""

    return AnalysisRetrievalSummary(
        id=model.id,
        paper_id=model.paper_id,
        paper_content_id=model.paper_content_id,
        analysis_scope=model.analysis_scope,
        status=model.status,
        schema_version=model.schema_version,
        provider=model.provider,
        model=model.model,
        prompt_version=model.prompt_version,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _to_chunk_summary(
    model: PaperChunk,
) -> PaperChunkRetrievalSummary:
    """Translate one chunk into explicit retrieval output."""

    return PaperChunkRetrievalSummary(
        id=model.id,
        paper_id=model.paper_id,
        paper_content_id=model.paper_content_id,
        section=model.section,
        heading=model.heading,
        sequence_number=model.sequence_number,
        text=model.text,
        start_char=model.start_char,
        end_char=model.end_char,
        paragraph_start_sequence=model.paragraph_start_sequence,
        paragraph_end_sequence=model.paragraph_end_sequence,
        token_count=model.token_count,
        page_number=model.page_number,
        end_page_number=model.end_page_number,
        chunker_version=model.chunker_version,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def explain_query(
    statement: Select[tuple[Any, ...]],
) -> str:
    """Render a query for manual PostgreSQL EXPLAIN inspection."""

    return str(statement)
