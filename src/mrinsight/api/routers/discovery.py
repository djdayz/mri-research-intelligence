from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from mrinsight.api.dependencies import (
    get_create_subscription_service,
    get_discovery_repository,
    get_run_digest_preview_service,
)
from mrinsight.api.schemas import (
    DigestPreviewRequest,
    DigestPreviewResponse,
    DigestResponse,
    SubscriptionCreateRequest,
    SubscriptionResponse,
    TopicResponse,
)
from mrinsight.application.services import (
    CreateSubscriptionService,
    RunDigestPreviewService,
    SubscriptionNotFoundError,
)
from mrinsight.discovery import DiscoveryRepository

router = APIRouter(
    tags=["discovery and digests"],
)


@router.get(
    "/topics",
    response_model=tuple[TopicResponse, ...],
)
def list_topics(
    repository: Annotated[
        DiscoveryRepository,
        Depends(get_discovery_repository),
    ],
) -> tuple[TopicResponse, ...]:
    """Return enabled discovery topics."""

    return tuple(TopicResponse.from_stored(topic) for topic in repository.list_topics())


@router.post(
    "/subscriptions",
    response_model=SubscriptionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_subscription(
    request: SubscriptionCreateRequest,
    service: Annotated[
        CreateSubscriptionService,
        Depends(get_create_subscription_service),
    ],
) -> SubscriptionResponse:
    """Create a discovery subscription."""

    subscription = service.execute(request.to_new_subscription())

    return SubscriptionResponse.from_stored(subscription)


@router.get(
    "/subscriptions",
    response_model=tuple[SubscriptionResponse, ...],
)
def list_subscriptions(
    repository: Annotated[
        DiscoveryRepository,
        Depends(get_discovery_repository),
    ],
) -> tuple[SubscriptionResponse, ...]:
    """List subscriptions."""

    return tuple(
        SubscriptionResponse.from_stored(subscription)
        for subscription in repository.list_subscriptions()
    )


@router.post(
    "/subscriptions/{subscription_id}/digest-preview",
    response_model=DigestPreviewResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_404_NOT_FOUND: {
            "description": "The subscription does not exist.",
        },
    },
)
def run_digest_preview(
    subscription_id: int,
    request: DigestPreviewRequest,
    service: Annotated[
        RunDigestPreviewService,
        Depends(get_run_digest_preview_service),
    ],
) -> DigestPreviewResponse:
    """Run discovery and create a rendered digest preview."""

    try:
        result = service.execute(
            subscription_id=subscription_id,
            period_start=request.period_start,
            period_end=request.period_end,
            rows=request.rows,
        )
    except SubscriptionNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The subscription does not exist.",
        ) from error

    return DigestPreviewResponse.from_result(result)


@router.get(
    "/digests/{digest_id}",
    response_model=DigestResponse,
    responses={
        status.HTTP_404_NOT_FOUND: {
            "description": "The digest does not exist.",
        },
    },
)
def get_digest(
    digest_id: int,
    repository: Annotated[
        DiscoveryRepository,
        Depends(get_discovery_repository),
    ],
) -> DigestResponse:
    """Return one rendered digest."""

    digest = repository.get_digest(digest_id)

    if digest is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The digest does not exist.",
        )

    return DigestResponse.from_stored(digest)
