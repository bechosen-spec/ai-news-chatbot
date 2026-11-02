"""FastAPI application factory."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.routes.admin_news import router as admin_news_router
from backend.app.api.routes.chat import router as chat_router
from backend.app.api.routes.health import router as health_router
from backend.app.api.routes.ml import router as ml_router
from backend.app.api.routes.news import router as news_router
from backend.app.core.config import Settings, get_settings
from backend.app.core.logging import configure_logging
from backend.app.db.session import create_database_engine, create_session_factory
from backend.app.services.llm.disabled import DisabledProvider
from backend.app.services.llm.openai import OpenAIResponsesProvider
from backend.app.services.model_service import ModelService, resolve_path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    settings.model_path = resolve_path(settings.model_path, PROJECT_ROOT)
    settings.model_metadata_path = resolve_path(settings.model_metadata_path, PROJECT_ROOT)
    configure_logging()
    engine = create_database_engine(settings.database_url)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        yield
        engine.dispose()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "Nigerian news metadata ingestion and topic classification service. "
            "Scores are not claims of truth, confidence, or bias."
        ),
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.engine = engine
    app.state.session_factory = create_session_factory(engine)
    app.state.model_service = ModelService(settings)
    app.state.llm_provider = (
        OpenAIResponsesProvider(settings)
        if settings.llm_provider == "openai"
        else DisabledProvider()
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Content-Type", "Authorization", "X-Admin-Key"],
    )
    app.include_router(health_router)
    app.include_router(ml_router)
    app.include_router(news_router)
    app.include_router(admin_news_router)
    app.include_router(chat_router)
    return app


app = create_app()
