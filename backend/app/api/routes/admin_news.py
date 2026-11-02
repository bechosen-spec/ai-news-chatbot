from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.app.api.dependencies.admin import require_admin_key
from backend.app.db.models import (
    AdministrativeAuditLog,
    ArticleCategory,
    IngestionRun,
    NewsArticle,
)
from backend.app.db.session import get_db
from backend.app.schemas.news import (
    ArticleAdminUpdate,
    IngestionRequest,
    IngestionRunResponse,
)
from backend.app.services.ingestion.rss import punch_adapter
from backend.app.services.ingestion.service import ingest

router = APIRouter(
    prefix="/api/v1/admin",
    tags=["news-administration"],
    dependencies=[Depends(require_admin_key)],
)
DBSession = Annotated[Session, Depends(get_db)]


@router.post("/news/ingest", response_model=IngestionRunResponse)
def ingest_news(
    payload: IngestionRequest,
    request: Request,
    session: DBSession,
):
    settings = request.app.state.settings
    adapter = punch_adapter(
        timeout_seconds=settings.ingestion_timeout_seconds,
        retry_limit=settings.ingestion_retry_limit,
        excerpt_max_characters=settings.news_excerpt_max_characters,
    )
    run = ingest(session, adapter, request.app.state.model_service, limit=payload.limit)
    session.add(
        AdministrativeAuditLog(
            actor="admin_api_key",
            action="news.ingest",
            target_type="ingestion_run",
            target_id=run.id,
            details={"source": payload.source, "limit": payload.limit},
        )
    )
    session.commit()
    return run


@router.get("/ingestion-runs", response_model=list[IngestionRunResponse])
def ingestion_runs(session: DBSession, limit: int = Query(default=25, ge=1, le=100)):
    return session.scalars(
        select(IngestionRun)
        .options(selectinload(IngestionRun.failures))
        .order_by(IngestionRun.started_at.desc())
        .limit(limit)
    ).all()


@router.patch("/news/{article_id}")
def update_article(
    article_id: str,
    payload: ArticleAdminUpdate,
    session: DBSession,
):
    article = session.get(NewsArticle, article_id)
    if article is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Article not found")
    changes: dict[str, object] = {}
    if "category_slug" in payload.model_fields_set:
        if payload.category_slug is None:
            article.admin_category = None
        else:
            category = session.scalar(
                select(ArticleCategory).where(ArticleCategory.slug == payload.category_slug)
            )
            if category is None:
                raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unknown category")
            article.admin_category = category
        changes["category_slug"] = payload.category_slug
    if "is_deleted" in payload.model_fields_set:
        article.deleted_at = datetime.now(UTC) if payload.is_deleted else None
        changes["is_deleted"] = payload.is_deleted
    if not changes:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="No changes supplied")
    session.add(
        AdministrativeAuditLog(
            actor="admin_api_key",
            action="news.update",
            target_type="news_article",
            target_id=article.id,
            details=changes,
        )
    )
    session.commit()
    return {"id": article.id, "updated": changes}


@router.delete("/news/{article_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_article(article_id: str, session: DBSession) -> None:
    article = session.get(NewsArticle, article_id)
    if article is None or article.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Article not found")
    article.deleted_at = datetime.now(UTC)
    session.add(
        AdministrativeAuditLog(
            actor="admin_api_key",
            action="news.soft_delete",
            target_type="news_article",
            target_id=article.id,
        )
    )
    session.commit()
