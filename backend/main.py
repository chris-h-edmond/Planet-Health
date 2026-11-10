"""Planet Health — FastAPI application entry point."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from api import analysis as analysis_api
from api import auth as auth_api
from api import dashboard as dashboard_api
from api import models as models_api
from core.config import get_settings
from core.database import dispose_engine, engine
from core.errors import register_exception_handlers
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from services.model_service import model_service

logger = logging.getLogger("planethealth")


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s %(name)s :: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan.

    The models are loaded exactly once here.  When the checkpoints are absent
    the application still starts and serves every unrelated endpoint; the
    prediction endpoint answers with HTTP 503 instead.
    """
    settings = get_settings()
    logger.info("Starting %s (env=%s)", settings.app_name, settings.app_env)

    status = model_service.load()
    logger.info("Model service status: %s", status.value)

    try:
        yield
    finally:
        logger.info("Shutting down %s", settings.app_name)
        model_service.shutdown()
        dispose_engine()


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "Planet Health is an AI-assisted plant monitoring platform. "
            "It exposes the plant stress classification and growth estimation "
            "models through a small, stable REST API."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    if settings.cors_allow_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_allow_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
            allow_headers=["Content-Type", "X-CSRF-Token", "Accept"],
            expose_headers=["X-Analysis-Id", "Location"],
        )

    register_exception_handlers(app)

    app.include_router(auth_api.router, prefix=settings.api_prefix)
    app.include_router(analysis_api.router, prefix=settings.api_prefix)
    app.include_router(dashboard_api.router, prefix=settings.api_prefix)
    app.include_router(models_api.router, prefix=settings.api_prefix)

    @app.get("/health", tags=["Health"], summary="Application health")
    def health() -> dict[str, object]:
        """Report application availability.

        Deliberately minimal — no server paths, versions of dependencies or
        other internal details are exposed.
        """
        database_state = "ok"
        try:
            with engine.connect() as connection:
                connection.exec_driver_sql("SELECT 1")
        except Exception:  # noqa: BLE001 - health must never raise
            database_state = "unavailable"

        return {
            "status": "ok" if database_state == "ok" else "degraded",
            "app": settings.app_name,
            "version": settings.app_version,
            "environment": settings.app_env,
            "database": database_state,
            "models": model_service.status.value,
            "timestamp": datetime.now(UTC).isoformat(),
        }

    return app


configure_logging()
app = create_app()
