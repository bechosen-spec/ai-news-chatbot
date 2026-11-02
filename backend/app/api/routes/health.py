from fastapi import APIRouter

from backend.app.core.config import get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    settings = get_settings()
    return {"status": "ok", "version": settings.app_version, "environment": settings.app_env}
