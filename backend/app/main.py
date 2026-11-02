"""FastAPI application factory."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.routes.health import router as health_router
from backend.app.api.routes.ml import router as ml_router
from backend.app.core.config import Settings, get_settings
from backend.app.core.logging import configure_logging
from backend.app.services.model_service import ModelService, resolve_path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    settings.model_path = resolve_path(settings.model_path, PROJECT_ROOT)
    settings.model_metadata_path = resolve_path(settings.model_metadata_path, PROJECT_ROOT)
    configure_logging()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        yield

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Phase 1 topic-classification service. Scores are not claims of truth or bias.",
        lifespan=lifespan,
    )
    app.state.model_service = ModelService(settings)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "Authorization"],
    )
    app.include_router(health_router)
    app.include_router(ml_router)
    return app


app = create_app()
