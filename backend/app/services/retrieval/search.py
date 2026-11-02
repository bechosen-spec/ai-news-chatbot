"""BM25-style retrieval with filters, deduplication, and source diversity reranking."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from backend.app.db.models import DataSource, NewsArticle
from backend.app.services.retrieval.text import normalize_tokens


@dataclass(frozen=True)
class Evidence:
    citation_id: str
    article_id: str
    title: str
    publisher: str
    source_slug: str | None
    url: str
    published_at: datetime | None
    excerpt: str
    category: str | None
    score: float


@dataclass(frozen=True)
class RetrievalResult:
    evidence: list[Evidence]
    query_terms: list[str]
    candidate_count: int
    unique_sources: int
    source_diversity_ratio: float
    limitations: list[str]


class Retriever:
    def __init__(self, session: Session, *, max_candidates: int = 500) -> None:
        self.session = session
        self.max_candidates = max_candidates

    def _candidates(
        self,
        *,
        category: str | None,
        source: str | None,
        published_after: datetime | None,
        published_before: datetime | None,
    ) -> list[NewsArticle]:
        statement = (
            select(NewsArticle)
            .join(NewsArticle.source)
            .join(NewsArticle.retrieval_metadata)
            .options(
                joinedload(NewsArticle.source),
                joinedload(NewsArticle.category),
                joinedload(NewsArticle.admin_category),
                joinedload(NewsArticle.retrieval_metadata),
            )
            .where(NewsArticle.deleted_at.is_(None), DataSource.is_active.is_(True))
            .order_by(NewsArticle.published_at.desc(), NewsArticle.collected_at.desc())
            .limit(self.max_candidates)
        )
        if source:
            statement = statement.where(DataSource.slug == source)
        if category:
            statement = statement.where(
                (NewsArticle.admin_category.has(slug=category))
                | (
                    NewsArticle.admin_category_id.is_(None)
                    & NewsArticle.category.has(slug=category)
                )
            )
        if published_after:
            statement = statement.where(NewsArticle.published_at >= published_after)
        if published_before:
            statement = statement.where(NewsArticle.published_at <= published_before)
        return list(self.session.scalars(statement).unique().all())

    @staticmethod
    def _effective_category(article: NewsArticle) -> str | None:
        category = article.admin_category or article.category
        return category.slug if category else None

    @staticmethod
    def _freshness(article: NewsArticle) -> float:
        published = article.published_at or article.collected_at
        if published.tzinfo is None:
            published = published.replace(tzinfo=UTC)
        age_days = max(0.0, (datetime.now(UTC) - published).total_seconds() / 86_400)
        return 0.15 / (1 + age_days / 30)

    def search(
        self,
        query: str,
        *,
        limit: int = 6,
        category: str | None = None,
        source: str | None = None,
        published_after: datetime | None = None,
        published_before: datetime | None = None,
        baseline: bool = False,
    ) -> RetrievalResult:
        terms = list(dict.fromkeys(normalize_tokens(query)))
        if not terms:
            return RetrievalResult([], [], 0, 0, 0.0, ["The query contained no searchable terms."])
        candidates = self._candidates(
            category=category,
            source=source,
            published_after=published_after,
            published_before=published_before,
        )
        if not candidates:
            return RetrievalResult(
                [], terms, 0, 0, 0.0, ["No indexed articles matched the filters."]
            )

        document_frequency = {
            term: sum(
                1
                for article in candidates
                if term in (article.retrieval_metadata.term_frequencies or {})
            )
            for term in terms
        }
        lengths = [max(1, article.retrieval_metadata.document_length) for article in candidates]
        average_length = sum(lengths) / len(lengths)
        scored: list[tuple[float, NewsArticle]] = []
        for article, length in zip(candidates, lengths, strict=True):
            frequencies = article.retrieval_metadata.term_frequencies or {}
            title_frequencies = article.retrieval_metadata.title_term_frequencies or {}
            if baseline:
                score = float(sum(1 for term in terms if frequencies.get(term, 0)))
            else:
                score = 0.0
                for term in terms:
                    frequency = frequencies.get(term, 0)
                    if not frequency:
                        continue
                    inverse_document_frequency = math.log(
                        1
                        + (len(candidates) - document_frequency[term] + 0.5)
                        / (document_frequency[term] + 0.5)
                    )
                    denominator = frequency + 1.2 * (0.25 + 0.75 * length / average_length)
                    score += inverse_document_frequency * frequency * 2.2 / denominator
                    score += 0.8 * min(2, title_frequencies.get(term, 0))
                if score > 0:
                    score += self._freshness(article)
            if score > 0:
                scored.append((score, article))

        scored.sort(
            key=lambda item: (
                item[0],
                item[1].published_at or item[1].collected_at,
                item[1].id,
            ),
            reverse=True,
        )
        selected: list[tuple[float, NewsArticle]] = []
        seen_urls: set[str] = set()
        seen_hashes: set[str] = set()
        source_counts: dict[str, int] = {}
        remaining = scored.copy()
        while remaining and len(selected) < limit:
            reranked = [
                (score / (1 + 0.35 * source_counts.get(article.source_id, 0)), score, article)
                for score, article in remaining
                if article.original_url not in seen_urls and article.content_hash not in seen_hashes
            ]
            if not reranked:
                break
            _, original_score, article = max(
                reranked,
                key=lambda item: (
                    item[0],
                    item[2].published_at or item[2].collected_at,
                    item[2].id,
                ),
            )
            selected.append((original_score, article))
            remaining.remove((original_score, article))
            seen_urls.add(article.original_url)
            seen_hashes.add(article.content_hash)
            source_counts[article.source_id] = source_counts.get(article.source_id, 0) + 1

        evidence = [
            Evidence(
                citation_id=f"S{position}",
                article_id=article.id,
                title=article.title,
                publisher=article.source.name,
                source_slug=article.source.slug,
                url=article.original_url,
                published_at=article.published_at,
                excerpt=(article.excerpt or article.content or "")[:1_500],
                category=self._effective_category(article),
                score=round(score, 6),
            )
            for position, (score, article) in enumerate(selected, start=1)
        ]
        unique_sources = len({item.source_slug or item.publisher for item in evidence})
        ratio = unique_sources / len(evidence) if evidence else 0.0
        limitations: list[str] = []
        if evidence and unique_sources < 2:
            limitations.append(
                "Only one publisher is available in the matched corpus; "
                "cross-source corroboration is not possible."
            )
        return RetrievalResult(
            evidence,
            terms,
            len(candidates),
            unique_sources,
            round(ratio, 4),
            limitations,
        )
