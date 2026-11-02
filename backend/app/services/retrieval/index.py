"""Materialize bounded lexical metadata for repeatable retrieval."""

import hashlib
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.db.models import NewsArticle, RetrievalMetadata
from backend.app.services.retrieval.text import normalize_tokens, term_frequencies

INDEX_VERSION = "bm25-v1"


def article_index_text(article: NewsArticle) -> str:
    return "\n".join(part for part in (article.title, article.excerpt, article.content) if part)


def index_article(session: Session, article: NewsArticle) -> RetrievalMetadata:
    text = article_index_text(article)
    text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
    metadata = article.retrieval_metadata
    if metadata is None and article.id:
        metadata = session.scalar(
            select(RetrievalMetadata).where(RetrievalMetadata.article_id == article.id)
        )
    if metadata is None:
        metadata = RetrievalMetadata(article=article, text_hash=text_hash)
        session.add(metadata)
    metadata.text_hash = text_hash
    metadata.index_version = INDEX_VERSION
    metadata.indexed_at = datetime.now(UTC)
    metadata.term_frequencies = term_frequencies(text)
    metadata.title_term_frequencies = term_frequencies(article.title)
    metadata.document_length = len(normalize_tokens(text, limit=10_000))
    return metadata


def reindex_all(session: Session, *, only_stale: bool = False) -> int:
    count = 0
    articles = session.scalars(
        select(NewsArticle).where(NewsArticle.deleted_at.is_(None)).order_by(NewsArticle.id)
    ).all()
    for article in articles:
        current_hash = hashlib.sha256(article_index_text(article).encode("utf-8")).hexdigest()
        if (
            only_stale
            and article.retrieval_metadata is not None
            and article.retrieval_metadata.text_hash == current_hash
            and article.retrieval_metadata.index_version == INDEX_VERSION
        ):
            continue
        index_article(session, article)
        count += 1
    session.commit()
    return count
