"""
FastAPI application factory.

Phase 1 exposes only a health check. Future phases will mount routers for
strategies, backtests, optimization, analytics, and MT5/EA endpoints.
"""

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from app.config.settings import get_settings
from app.database.db_manager import get_database_manager
from app.utils.logger import get_logger

logger = get_logger(__name__)


def create_app() -> FastAPI:
    """Build and return the configured FastAPI application."""
    settings = get_settings()

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        get_database_manager().initialize()
        logger.info("%s API started (environment=%s)", settings.app_name, settings.environment)
        yield

    app = FastAPI(
        title=settings.app_name,
        description="Institutional-grade AI Strategy Research Platform.",
        version="0.1.0",
        lifespan=lifespan,
    )

    @app.get("/health", tags=["system"])
    def health() -> dict[str, str]:
        return {"status": "ok", "app": settings.app_name, "environment": settings.environment}

    return app


app = create_app()
