from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session, sessionmaker

from mrinsight.api.dependencies import get_database_session_factory
from mrinsight.core.config import Settings, get_settings
from mrinsight.db.health import check_database_connection


class HealthResponse(BaseModel):
    """Response returned by the health endpoint"""

    status: Literal["ok"]
    service: str


class ReadinessResponse(BaseModel):
    """Response returned by the readiness endpoint."""

    status: Literal["ready"]
    service: str
    database: Literal["ok"]


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


@router.get("/ready", response_model=ReadinessResponse)
def readiness_check(
    settings: Annotated[Settings, Depends(get_settings)],
    session_factory: Annotated[
        sessionmaker[Session],
        Depends(get_database_session_factory),
    ],
) -> ReadinessResponse:
    """Report whether required runtime dependencies are reachable."""

    try:
        check_database_connection(session_factory)
    except Exception as error:
        raise HTTPException(
            status_code=503,
            detail="Database is not reachable.",
        ) from error

    return ReadinessResponse(
        status="ready",
        service=settings.service_name,
        database="ok",
    )
