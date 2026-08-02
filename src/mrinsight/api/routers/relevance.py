from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status

from mrinsight.api.dependencies import get_assess_paper_relevance_service
from mrinsight.api.schemas import RelevanceAssessmentResponse
from mrinsight.application.services import (
    AssessPaperRelevanceService,
    NoAnalyzableContentError,
    PaperNotFoundError,
)

router = APIRouter(
    prefix="/papers",
    tags=["paper relevance"],
)


@router.post(
    "/{paper_id}/relevance",
    response_model=RelevanceAssessmentResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_200_OK: {
            "description": "The current relevance assessment was reused.",
        },
        status.HTTP_404_NOT_FOUND: {
            "description": "The paper does not exist.",
        },
        status.HTTP_422_UNPROCESSABLE_ENTITY: {
            "description": "The paper has no analyzable content.",
        },
    },
)
def assess_paper_relevance(
    paper_id: int,
    response: Response,
    service: Annotated[
        AssessPaperRelevanceService,
        Depends(get_assess_paper_relevance_service),
    ],
) -> RelevanceAssessmentResponse:
    """Compute or retrieve deterministic MRI/CVR relevance."""

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

    if result.cached:
        response.status_code = status.HTTP_200_OK

    return RelevanceAssessmentResponse.from_result(result)
