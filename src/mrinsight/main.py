from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, Request, Response

from mrinsight import __version__
from mrinsight.api.dependencies import (
    close_application_resources,
)
from mrinsight.api.routers.analysis import (
    router as analysis_router,
)
from mrinsight.api.routers.discovery import (
    router as discovery_router,
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
from mrinsight.api.routers.retrieval import (
    router as retrieval_router,
)
from mrinsight.core.config import get_settings
from mrinsight.core.logging import configure_logging, log_event


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
    configure_logging(level=settings.log_level)

    application = FastAPI(
        title=settings.app_name,
        version=__version__,
        lifespan=lifespan,
    )

    application.include_router(health_router)
    application.include_router(papers_router)
    application.include_router(retrieval_router)
    application.include_router(full_text_router)
    application.include_router(relevance_router)
    application.include_router(analysis_router)
    application.include_router(discovery_router)

    return application


async def add_request_context(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """Attach request identifiers and emit one structured completion event."""

    request_id = request.headers.get("x-request-id") or str(uuid4())
    started_at = perf_counter()
    status_code = 500

    try:
        response = await call_next(request)
        status_code = response.status_code
    except Exception:
        log_event(
            "http_request_failed",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            status_code=status_code,
            duration_ms=round((perf_counter() - started_at) * 1000, 2),
        )
        raise

    response.headers["x-request-id"] = request_id
    log_event(
        "http_request_completed",
        request_id=request_id,
        method=request.method,
        path=request.url.path,
        status_code=status_code,
        duration_ms=round((perf_counter() - started_at) * 1000, 2),
    )

    return response


app = create_app()
app.middleware("http")(add_request_context)
