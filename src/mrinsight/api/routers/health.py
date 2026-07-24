from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from mrinsight.core.config import Settings, get_settings


class HealthResponse(BaseModel):
    """Response returned by the health endpoint"""

    status: Literal["ok"]
    service: str


router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health_check(
    settings: Annotated[Settings, Depends(get_settings)],
) -> HealthResponse:
    """Report whether the API process is running"""

    return HealthResponse(
        status="ok",
        service=settings.service_name,
    )
