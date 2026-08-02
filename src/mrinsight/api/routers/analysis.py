from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status

from mrinsight.analysis.repositories import PaperAnalysisRepository
from mrinsight.api.dependencies import (
    get_analyze_paper_service,
    get_paper_analysis_repository,
    get_paper_repository,
)
from mrinsight.api.schemas import PaperAnalysisResponse
from mrinsight.application.services import (
    AnalyzePaperService,
    NoAnalyzableContentError,
    PaperAnalysisOutcome,
    PaperNotFoundError,
)
from mrinsight.papers.repositories import PaperRepository

router = APIRouter(
    tags=["paper analysis"],
)


@router.post(
    "/papers/{paper_id}/analysis",
    response_model=PaperAnalysisResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_200_OK: {
            "description": "A current successful analysis was reused.",
        },
        status.HTTP_404_NOT_FOUND: {
            "description": "The paper does not exist.",
        },
        status.HTTP_422_UNPROCESSABLE_ENTITY: {
            "description": "The paper is not eligible for analysis.",
        },
        status.HTTP_502_BAD_GATEWAY: {
            "description": "The provider output failed validation.",
        },
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "description": "The LLM provider is unconfigured or unavailable.",
        },
    },
)
def analyze_paper(
    paper_id: int,
    response: Response,
    service: Annotated[
        AnalyzePaperService,
        Depends(get_analyze_paper_service),
    ],
) -> PaperAnalysisResponse:
    """Compute or retrieve structured scientific analysis."""

    try:
        result = service.execute(paper_id)
    except PaperNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The paper does not exist.",
        ) from error
    except NoAnalyzableContentError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The paper has no analyzable content.",
        ) from error

    if result.outcome is PaperAnalysisOutcome.CACHED:
        response.status_code = status.HTTP_200_OK
    elif result.outcome is PaperAnalysisOutcome.PROVIDER_FAILED:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    elif result.outcome is PaperAnalysisOutcome.FAILED:
        response.status_code = status.HTTP_502_BAD_GATEWAY
    elif result.outcome is PaperAnalysisOutcome.INELIGIBLE:
        response.status_code = status.HTTP_422_UNPROCESSABLE_ENTITY

    return PaperAnalysisResponse.from_result(result)


@router.get(
    "/papers/{paper_id}/analysis",
    response_model=tuple[PaperAnalysisResponse, ...],
    responses={
        status.HTTP_404_NOT_FOUND: {
            "description": "The paper does not exist.",
        },
    },
)
def list_paper_analyses(
    paper_id: int,
    paper_repository: Annotated[
        PaperRepository,
        Depends(get_paper_repository),
    ],
    analysis_repository: Annotated[
        PaperAnalysisRepository,
        Depends(get_paper_analysis_repository),
    ],
) -> tuple[PaperAnalysisResponse, ...]:
    """Return persisted analyses for one paper."""

    if paper_repository.get_by_id(paper_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The paper does not exist.",
        )

    return tuple(
        PaperAnalysisResponse.from_stored(analysis)
        for analysis in analysis_repository.list_by_paper(paper_id)
    )


@router.get(
    "/analyses/{analysis_id}",
    response_model=PaperAnalysisResponse,
    responses={
        status.HTTP_404_NOT_FOUND: {
            "description": "The analysis does not exist.",
        },
    },
)
def get_analysis(
    analysis_id: int,
    repository: Annotated[
        PaperAnalysisRepository,
        Depends(get_paper_analysis_repository),
    ],
) -> PaperAnalysisResponse:
    """Return one persisted structured analysis."""

    analysis = repository.get_by_id(analysis_id)

    if analysis is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The analysis does not exist.",
        )

    return PaperAnalysisResponse.from_stored(analysis)
