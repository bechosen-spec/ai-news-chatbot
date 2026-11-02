from datetime import UTC, datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.app.db.base import Base
from backend.app.db.models import ArticleCategory, DataSource, NewsArticle
from backend.app.services.retrieval import Retriever
from backend.app.services.retrieval.index import index_article


def _article(source, category, title, excerpt, url, *, days_old=0, content_hash=None):
    return NewsArticle(
        source=source,
        category=category,
        title=title,
        content="",
        excerpt=excerpt,
        original_url=url,
        content_hash=content_hash or url.rsplit("/", 1)[-1].ljust(64, "x")[:64],
        published_at=datetime.now(UTC) - timedelta(days=days_old),
    )


def test_bm25_retrieval_filters_deduplicates_and_reports_diversity():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as session:
        punch = DataSource(
            name="Punch", slug="punch", base_url="https://punch.test", ingestion_method="rss"
        )
        wire = DataSource(
            name="Example Wire", slug="wire", base_url="https://wire.test", ingestion_method="rss"
        )
        politics = ArticleCategory(slug="politics", display_name="Politics")
        rows = [
            _article(
                punch,
                politics,
                "Police recover stolen cables in Gombe",
                "Officers arrested a vandal and recovered copper wires.",
                "https://punch.test/gombe-cables",
            ),
            _article(
                wire,
                politics,
                "Gombe cable vandal arrested",
                "Police said stolen wires were recovered.",
                "https://wire.test/gombe-vandal",
            ),
            _article(
                punch,
                politics,
                "Sports team wins final",
                "The match ended with two goals.",
                "https://punch.test/sport",
            ),
        ]
        session.add_all(rows)
        session.flush()
        for row in rows:
            index_article(session, row)
        session.commit()

        result = Retriever(session).search("What cables did police recover in Gombe?", limit=3)
        assert [item.article_id for item in result.evidence[:2]] == [rows[0].id, rows[1].id]
        assert result.unique_sources == 2
        assert result.source_diversity_ratio == 1.0
        filtered = Retriever(session).search("Gombe cables", source="wire")
        assert [item.source_slug for item in filtered.evidence] == ["wire"]


def test_empty_query_is_safe_and_deterministic():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        result = Retriever(session).search("the and what")
    assert result.evidence == []
    assert result.limitations == ["The query contained no searchable terms."]
