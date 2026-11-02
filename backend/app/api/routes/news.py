import math
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.db.models import ArticleCategory, DataSource, NewsArticle
from backend.app.db.session import get_db
from backend.app.schemas.news import (
    ArticleDetail,
    ArticleSummary,
    CategoryResponse,
    PaginatedArticles,
    SourceResponse,
)
from backend.app.services.news.query import (
    article_query,
    current_prediction,
    effective_category,
    filter_articles,
    paginate,
    search_statement,
)

router = APIRouter(prefix="/api/v1/news", tags=["news"])
DBSession = Annotated[Session, Depends(get_db)]


def _summary(article: NewsArticle) -> ArticleSummary:
    return ArticleSummary(
        id=article.id,
        title=article.title,
        excerpt=article.excerpt,
        original_url=article.original_url,
        publisher=article.source.name,
        source_slug=article.source.slug,
        source_category=article.source_category,
        category=effective_category(article),
        published_at=article.published_at,
        collected_at=article.collected_at,
        image_url=article.image_url,
    )


def _page(items, total: int, page: int, page_size: int) -> PaginatedArticles:
    return PaginatedArticles(
        items=[_summary(article) for article in items],
        page=page,
        page_size=page_size,
        total=total,
        pages=math.ceil(total / page_size) if total else 0,
    )


@router.get("", response_model=PaginatedArticles)
def list_news(
    session: DBSession,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    category: str | None = None,
    source: str | None = None,
    sort: Literal["newest", "oldest"] = "newest",
) -> PaginatedArticles:
    statement = filter_articles(article_query(), category=category, source=source)
    order = NewsArticle.published_at.asc() if sort == "oldest" else NewsArticle.published_at.desc()
    items, total = paginate(
        session,
        statement.order_by(order, NewsArticle.collected_at.desc()),
        page=page,
        page_size=page_size,
    )
    return _page(items, total, page, page_size)


@router.get("/search", response_model=PaginatedArticles)
def search_news(
    session: DBSession,
    q: str = Query(min_length=2, max_length=200),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    category: str | None = None,
    source: str | None = None,
) -> PaginatedArticles:
    statement = filter_articles(search_statement(q), category=category, source=source)
    statement = statement.order_by(NewsArticle.published_at.desc(), NewsArticle.collected_at.desc())
    items, total = paginate(session, statement, page=page, page_size=page_size)
    return _page(items, total, page, page_size)


@router.get("/categories", response_model=list[CategoryResponse])
def categories(session: DBSession):
    return session.scalars(select(ArticleCategory).order_by(ArticleCategory.display_name)).all()


@router.get("/sources", response_model=list[SourceResponse])
def sources(session: DBSession):
    return session.scalars(
        select(DataSource).where(DataSource.is_active.is_(True)).order_by(DataSource.name)
    ).all()


@router.get("/{article_id}", response_model=ArticleDetail)
def article_detail(article_id: str, session: DBSession) -> ArticleDetail:
    article = session.scalar(article_query().where(NewsArticle.id == article_id))
    if article is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Article not found")
    prediction = current_prediction(article)
    classification = None
    if prediction:
        classification = {
            "predicted_category": prediction.predicted_category,
            "model_id": prediction.model_id,
            "model_version": prediction.model_version,
            "score_type": prediction.score_type,
            "top_score": prediction.top_score,
            "administrator_corrected": article.admin_category_id is not None,
        }
    return ArticleDetail(
        **_summary(article).model_dump(),
        author=article.author,
        language=article.language,
        classification=classification,
    )
