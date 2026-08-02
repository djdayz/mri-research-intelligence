from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from mrinsight.analysis.records import PaperAnalysisStatus
from mrinsight.api.dependencies import get_paper_retrieval_repository
from mrinsight.api.schemas import (
    ContentSummaryResponse,
    PaperChunkSearchResponse,
    PaperDetailResponse,
    PaperSearchResponse,
)
from mrinsight.papers import (
    AnalysisScope,
    ContentType,
    ExtractionStatus,
    InvalidDOIError,
    InvalidTitleError,
    SectionType,
    normalize_doi,
    normalize_title,
)
from mrinsight.relevance import RelevanceLabel
from mrinsight.retrieval import (
    PageRequest,
    PaperRetrievalRepository,
    PaperSearchFilters,
    PaperSort,
)

DEFAULT_LIMIT = 25
MAX_PAPER_LIMIT = 100
MAX_CHUNK_LIMIT = 200

router = APIRouter(
    prefix="/papers",
    tags=["paper retrieval"],
)


@router.get(
    "",
    response_model=PaperSearchResponse,
)
def list_papers(
    repository: Annotated[
        PaperRetrievalRepository,
        Depends(get_paper_retrieval_repository),
    ],
    limit: Annotated[
        int,
        Query(ge=1, le=MAX_PAPER_LIMIT),
    ] = DEFAULT_LIMIT,
    offset: Annotated[
        int,
        Query(ge=0),
    ] = 0,
    sort: PaperSort = PaperSort.NEWEST_INGESTION,
    doi: Annotated[
        str | None,
        Query(min_length=1),
    ] = None,
    title_query: Annotated[
        str | None,
        Query(min_length=1),
    ] = None,
    publication_date_from: date | None = None,
    publication_date_to: date | None = None,
    journal: Annotated[
        str | None,
        Query(min_length=1),
    ] = None,
    ingestion_source: Annotated[
        str | None,
        Query(min_length=1),
    ] = None,
    content_scope: ContentType | None = None,
    extraction_status: ExtractionStatus | None = None,
    relevance_label: RelevanceLabel | None = None,
    mri_category: Annotated[
        str | None,
        Query(min_length=1),
    ] = None,
    analysis_status: PaperAnalysisStatus | None = None,
    analysis_scope: AnalysisScope | None = None,
) -> PaperSearchResponse:
    """List papers with bounded offset pagination, filters, and stable sorting."""

    filters = _build_filters(
        doi=doi,
        title_query=title_query,
        publication_date_from=publication_date_from,
        publication_date_to=publication_date_to,
        journal=journal,
        ingestion_source=ingestion_source,
        content_scope=content_scope,
        extraction_status=extraction_status,
        relevance_label=relevance_label,
        mri_category=mri_category,
        analysis_status=analysis_status,
        analysis_scope=analysis_scope,
    )
    result = repository.search_papers(
        filters=filters,
        page=PageRequest(limit=limit, offset=offset),
        sort=sort,
    )

    return PaperSearchResponse.from_result(result)


@router.get(
    "/{paper_id}",
    response_model=PaperDetailResponse,
    responses={
        status.HTTP_404_NOT_FOUND: {
            "description": "The paper does not exist.",
        },
    },
)
def get_paper(
    paper_id: int,
    repository: Annotated[
        PaperRetrievalRepository,
        Depends(get_paper_retrieval_repository),
    ],
) -> PaperDetailResponse:
    """Return paper detail and related resource summaries."""

    result = repository.get_paper_detail(paper_id)

    if not result.items:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The paper does not exist.",
        )

    return PaperDetailResponse.from_summary(result.items[0])


@router.get(
    "/{paper_id}/contents",
    response_model=tuple[ContentSummaryResponse, ...],
    responses={
        status.HTTP_404_NOT_FOUND: {
            "description": "The paper does not exist.",
        },
    },
)
def list_paper_contents(
    paper_id: int,
    repository: Annotated[
        PaperRetrievalRepository,
        Depends(get_paper_retrieval_repository),
    ],
) -> tuple[ContentSummaryResponse, ...]:
    """Return content metadata without extracted full text."""

    summaries = repository.list_contents(paper_id)

    if summaries is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The paper does not exist.",
        )

    return tuple(ContentSummaryResponse.from_summary(summary) for summary in summaries)


@router.get(
    "/{paper_id}/chunks",
    response_model=PaperChunkSearchResponse,
    responses={
        status.HTTP_404_NOT_FOUND: {
            "description": "The paper does not exist.",
        },
    },
)
def list_paper_chunks(
    paper_id: int,
    repository: Annotated[
        PaperRetrievalRepository,
        Depends(get_paper_retrieval_repository),
    ],
    limit: Annotated[
        int,
        Query(ge=1, le=MAX_CHUNK_LIMIT),
    ] = DEFAULT_LIMIT,
    offset: Annotated[
        int,
        Query(ge=0),
    ] = 0,
    content_id: Annotated[
        int | None,
        Query(gt=0),
    ] = None,
    section: SectionType | None = None,
) -> PaperChunkSearchResponse:
    """Return explicit evidence chunks for a paper."""

    result = repository.search_chunks(
        paper_id=paper_id,
        content_id=content_id,
        section=section.value if section is not None else None,
        page=PageRequest(limit=limit, offset=offset),
    )

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The paper does not exist.",
        )

    return PaperChunkSearchResponse.from_result(result)


def _build_filters(
    *,
    doi: str | None,
    title_query: str | None,
    publication_date_from: date | None,
    publication_date_to: date | None,
    journal: str | None,
    ingestion_source: str | None,
    content_scope: ContentType | None,
    extraction_status: ExtractionStatus | None,
    relevance_label: RelevanceLabel | None,
    mri_category: str | None,
    analysis_status: PaperAnalysisStatus | None,
    analysis_scope: AnalysisScope | None,
) -> PaperSearchFilters:
    """Build normalized retrieval filters from public query params."""

    if (
        publication_date_from is not None
        and publication_date_to is not None
        and publication_date_to < publication_date_from
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="publication_date_to cannot be before publication_date_from.",
        )

    try:
        normalized_doi = normalize_doi(doi) if doi is not None else None
    except InvalidDOIError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid DOI filter.",
        ) from error

    try:
        normalized_title_query = (
            normalize_title(title_query) if title_query is not None else None
        )
    except InvalidTitleError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid title query.",
        ) from error

    return PaperSearchFilters(
        doi=normalized_doi,
        title_query=normalized_title_query,
        publication_date_from=publication_date_from,
        publication_date_to=publication_date_to,
        journal=journal,
        ingestion_source=ingestion_source,
        content_scope=content_scope.value if content_scope is not None else None,
        extraction_status=(
            extraction_status.value if extraction_status is not None else None
        ),
        relevance_label=relevance_label.value if relevance_label is not None else None,
        mri_category=mri_category,
        analysis_status=(
            analysis_status.value if analysis_status is not None else None
        ),
        analysis_scope=analysis_scope.value if analysis_scope is not None else None,
    )
