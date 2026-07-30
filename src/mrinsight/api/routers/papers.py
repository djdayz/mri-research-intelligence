from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Response,
    status,
)
from sqlalchemy.exc import IntegrityError

from mrinsight.api.dependencies import (
    get_ingest_paper_service,
)
from mrinsight.api.schemas import (
    IngestPaperRequest,
    IngestPaperResponse,
)
from mrinsight.application.services import (
    BibliographicIdentityMismatchError,
    IngestPaperService,
)
from mrinsight.papers.providers import (
    BibliographicProviderError,
    BibliographicProviderUnavailableError,
    BibliographicRecordNotFoundError,
    InvalidBibliographicResponseError,
)

router = APIRouter(
    prefix="/papers",
    tags=["papers"],
)


@router.post(
    "",
    response_model=IngestPaperResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_200_OK: {
            "description": "The paper already existed.",
        },
        status.HTTP_404_NOT_FOUND: {
            "description": "No record was found for the DOI.",
        },
        status.HTTP_409_CONFLICT: {
            "description": "A concurrent duplicate was detected.",
        },
        status.HTTP_502_BAD_GATEWAY: {
            "description": "The provider returned invalid data.",
        },
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "description": "The provider is temporarily unavailable.",
        },
    },
)
def ingest_paper(
    request: IngestPaperRequest,
    response: Response,
    service: Annotated[
        IngestPaperService,
        Depends(get_ingest_paper_service),
    ],
) -> IngestPaperResponse:
    """Resolve and persist one paper using its DOI."""

    try:
        result = service.execute(request.doi)
    except BibliographicRecordNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=("No bibliographic record was found by the configured provider."),
        ) from error
    except BibliographicProviderUnavailableError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The bibliographic provider is unavailable.",
        ) from error
    except (
        InvalidBibliographicResponseError,
        BibliographicIdentityMismatchError,
    ) as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=("The bibliographic provider returned inconsistent metadata."),
        ) from error
    except BibliographicProviderError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Bibliographic metadata resolution failed.",
        ) from error
    except IntegrityError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A paper with this DOI already exists.",
        ) from error

    if result.created:
        response.status_code = status.HTTP_201_CREATED
    else:
        response.status_code = status.HTTP_200_OK

    return IngestPaperResponse.from_result(result)
