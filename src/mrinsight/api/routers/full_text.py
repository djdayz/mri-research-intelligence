from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Response,
    UploadFile,
    status,
)

from mrinsight.api.dependencies import (
    get_ingest_full_text_service,
    get_pdf_upload_policy,
    get_select_analysis_content_service,
)
from mrinsight.api.schemas import (
    FullTextUploadResponse,
)
from mrinsight.application.services import (
    FullTextIngestionOutcome,
    IngestFullTextService,
    NoAnalyzableContentError,
    PaperNotFoundError,
    SelectAnalysisContentService,
)
from mrinsight.documents import (
    DocumentAccessBasis,
    InvalidPdfUploadError,
    PdfFileTooLargeError,
    PdfUploadCandidate,
    PdfUploadPolicy,
    UnsupportedPdfMediaTypeError,
)

router = APIRouter(
    prefix="/papers",
    tags=["paper full text"],
)


@router.post(
    "/{paper_id}/full-text",
    response_model=FullTextUploadResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_200_OK: {
            "description": "Full text was reused or replaced.",
        },
        status.HTTP_404_NOT_FOUND: {
            "description": "The paper does not exist.",
        },
        status.HTTP_413_REQUEST_ENTITY_TOO_LARGE: {
            "description": "The PDF exceeds the size limit.",
        },
        status.HTTP_415_UNSUPPORTED_MEDIA_TYPE: {
            "description": "The upload is not a supported PDF.",
        },
        status.HTTP_422_UNPROCESSABLE_ENTITY: {
            "description": "The PDF is invalid or has no extractable text.",
        },
    },
)
async def upload_full_text(
    paper_id: int,
    response: Response,
    file: Annotated[
        UploadFile,
        File(description="User-supplied scientific PDF"),
    ],
    service: Annotated[
        IngestFullTextService,
        Depends(get_ingest_full_text_service),
    ],
    selector: Annotated[
        SelectAnalysisContentService,
        Depends(get_select_analysis_content_service),
    ],
    policy: Annotated[
        PdfUploadPolicy,
        Depends(get_pdf_upload_policy),
    ],
) -> FullTextUploadResponse:
    """Validate, extract and persist one paper PDF."""

    try:
        data = await file.read(policy.max_bytes + 1)
    finally:
        await file.close()

    candidate = PdfUploadCandidate(
        filename=file.filename or "",
        content_type=file.content_type,
        data=data,
        access_basis=DocumentAccessBasis.USER_UPLOAD,
    )

    try:
        result = service.execute(
            paper_id,
            candidate,
        )
    except PaperNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The paper does not exist.",
        ) from error
    except PdfFileTooLargeError as error:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="The PDF exceeds the configured size limit.",
        ) from error
    except UnsupportedPdfMediaTypeError as error:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="The upload is not a supported PDF.",
        ) from error
    except InvalidPdfUploadError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from error

    try:
        selected = selector.execute(paper_id)
        analysis_scope = selected.scope
    except NoAnalyzableContentError:
        analysis_scope = None

    if result.outcome is FullTextIngestionOutcome.CREATED:
        response.status_code = status.HTTP_201_CREATED
    elif result.outcome is FullTextIngestionOutcome.FAILED:
        response.status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    else:
        response.status_code = status.HTTP_200_OK

    return FullTextUploadResponse.from_result(
        paper_id=paper_id,
        result=result,
        analysis_scope=analysis_scope,
    )
