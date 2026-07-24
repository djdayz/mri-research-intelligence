from fastapi import FastAPI

from mrinsight.api.routers.health import router as health_router
from mrinsight.core.config import get_settings


def create_app() -> FastAPI:
    """Create and configure the FastAPI application"""

    settings = get_settings()

    application = FastAPI(
        title=settings.app_name,
        version="0.1.0",
    )

    application.include_router(health_router)

    return application


# For uvicorn: `uvicorn src.mrinsight.main:app --reload`
app = create_app()
