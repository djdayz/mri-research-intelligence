from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from mrinsight.api.dependencies import (
    close_application_resources,
)
from mrinsight.api.routers.full_text import (
    router as full_text_router,
)
from mrinsight.api.routers.health import (
    router as health_router,
)
from mrinsight.api.routers.papers import (
    router as papers_router,
)
from mrinsight.api.routers.relevance import (
    router as relevance_router,
)
from mrinsight.core.config import get_settings


@asynccontextmanager
async def lifespan(
    application: FastAPI,
) -> AsyncIterator[None]:
    """Manage process-wide application resources."""

    del application

    try:
        yield
    finally:
        close_application_resources()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    settings = get_settings()

    application = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        lifespan=lifespan,
    )

    application.include_router(health_router)
    application.include_router(papers_router)
    application.include_router(full_text_router)
    application.include_router(relevance_router)

    return application


app = create_app()
