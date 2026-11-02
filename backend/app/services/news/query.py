from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from backend.app.db.models import DataSource, NewsArticle


def article_query():
    return (
        select(NewsArticle)
        .options(
            selectinload(NewsArticle.source),
            selectinload(NewsArticle.category),
            selectinload(NewsArticle.admin_category),
            selectinload(NewsArticle.predictions),
        )
        .where(NewsArticle.deleted_at.is_(None))
    )


def filter_articles(statement, *, category: str | None = None, source: str | None = None):
    if category:
        statement = statement.where(
            or_(
                NewsArticle.admin_category.has(slug=category),
                (NewsArticle.admin_category_id.is_(None) & NewsArticle.category.has(slug=category)),
            )
        )
    if source:
        statement = statement.where(NewsArticle.source.has(DataSource.slug == source))
    return statement


def paginate(session: Session, statement, *, page: int, page_size: int):
    count_statement = select(func.count()).select_from(statement.order_by(None).subquery())
    total = session.scalar(count_statement) or 0
    items = session.scalars(statement.offset((page - 1) * page_size).limit(page_size)).all()
    return items, total


def search_statement(query: str):
    pattern = f"%{query}%"
    return article_query().where(
        or_(NewsArticle.title.ilike(pattern), NewsArticle.excerpt.ilike(pattern))
    )


def effective_category(article: NewsArticle) -> str | None:
    category = article.admin_category or article.category
    return category.slug if category else None


def current_prediction(article: NewsArticle):
    current = [prediction for prediction in article.predictions if prediction.is_current]
    if not current:
        return None
    return max(current, key=lambda prediction: prediction.created_at)
