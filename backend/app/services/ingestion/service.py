"""Fetch, validate, deduplicate, classify, and persist news metadata."""

from __future__ import annotations

import hashlib
import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.db.models import (
    ArticleCategory,
    ClassificationPrediction,
    DataSource,
    IngestionFailure,
    IngestionRun,
    NewsArticle,
)
from backend.app.services.model_service import ModelService, ModelUnavailableError
from backend.app.services.retrieval.index import index_article
from shared.news import NewsSourceAdapter

LOGGER = logging.getLogger(__name__)
SUPPORTED_CATEGORIES = ("business", "entertainment", "politics", "sport", "tech")


def _ensure_categories(session: Session) -> dict[str, ArticleCategory]:
    existing = {row.slug: row for row in session.scalars(select(ArticleCategory)).all()}
    for slug in SUPPORTED_CATEGORIES:
        if slug not in existing:
            category = ArticleCategory(slug=slug, display_name=slug.title())
            session.add(category)
            existing[slug] = category
    session.flush()
    return existing


def _ensure_source(session: Session, adapter: NewsSourceAdapter) -> DataSource:
    descriptor = adapter.descriptor
    source = session.scalar(select(DataSource).where(DataSource.slug == descriptor.slug))
    if source is None:
        source = DataSource(
            name=descriptor.name,
            slug=descriptor.slug,
            base_url=descriptor.base_url,
            ingestion_method=descriptor.ingestion_method,
            feed_url=descriptor.feed_url,
            terms_url=descriptor.terms_url,
            is_active=True,
        )
        session.add(source)
        session.flush()
    return source


def _safe_message(error: Exception) -> str:
    return str(error).replace("\n", " ")[:1_000] or type(error).__name__


def ingest(
    session: Session,
    adapter: NewsSourceAdapter,
    model_service: ModelService,
    *,
    limit: int | None = 50,
) -> IngestionRun:
    categories = _ensure_categories(session)
    source = _ensure_source(session, adapter)
    run = IngestionRun(source=source, status="running", requested_limit=limit)
    session.add(run)
    session.commit()

    try:
        for incoming in adapter.fetch(limit=limit):
            run.fetched_count += 1
            existing = session.scalar(
                select(NewsArticle.id).where(
                    (NewsArticle.original_url == incoming.original_url)
                    | (
                        (NewsArticle.source_id == source.id)
                        & (NewsArticle.source_external_id == incoming.external_id)
                    )
                )
            )
            if existing:
                run.duplicate_count += 1
                continue
            classification_input = "\n\n".join(
                part for part in (incoming.title, incoming.content) if part
            )
            try:
                result = model_service.classify(classification_input)
            except ModelUnavailableError as error:
                run.failed_count += 1
                session.add(
                    IngestionFailure(
                        run=run,
                        stage="classification",
                        reference=incoming.original_url,
                        error_type=type(error).__name__,
                        message=_safe_message(error),
                    )
                )
                continue
            predicted = result["predicted_category"]
            article = NewsArticle(
                source=source,
                category=categories[predicted],
                source_external_id=incoming.external_id,
                title=incoming.title,
                content="",
                excerpt=incoming.content,
                author=incoming.author,
                source_category=incoming.category,
                language=incoming.language,
                image_url=incoming.image_url,
                source_metadata=incoming.metadata,
                original_url=incoming.original_url,
                content_hash=hashlib.sha256(classification_input.encode()).hexdigest(),
                published_at=incoming.published_at,
                collected_at=incoming.collected_at or datetime.now(UTC),
            )
            scores = result["scores"]
            article.predictions.append(
                ClassificationPrediction(
                    model_id=result["model_id"],
                    model_version=result["model_version"],
                    predicted_category=predicted,
                    score_type=result["score_type"],
                    top_score=max(score["value"] for score in scores),
                    scores=scores,
                    input_hash=article.content_hash,
                    is_current=True,
                )
            )
            session.add(article)
            session.flush()
            index_article(session, article)
            run.inserted_count += 1

        for failure in adapter.failures:
            run.failed_count += 1
            session.add(
                IngestionFailure(
                    run=run,
                    stage="fetch",
                    reference=failure.feed_url,
                    error_type=failure.error_type,
                    message=failure.message[:1_000],
                )
            )
        run.status = "completed" if run.failed_count == 0 else "partial"
        if run.inserted_count or run.duplicate_count:
            source.last_success_at = datetime.now(UTC)
    except Exception as error:
        LOGGER.exception("Unexpected ingestion failure source=%s", source.slug)
        run.failed_count += 1
        run.status = "failed"
        session.add(
            IngestionFailure(
                run=run,
                stage="pipeline",
                error_type=type(error).__name__,
                message=_safe_message(error),
            )
        )
    run.completed_at = datetime.now(UTC)
    session.commit()
    session.refresh(run)
    return run
