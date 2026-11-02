from datetime import UTC, datetime

import httpx
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from backend.app.db.base import Base
from backend.app.db.models import ClassificationPrediction, IngestionFailure, NewsArticle
from backend.app.services.ingestion.rss import RSSFeedAdapter
from backend.app.services.ingestion.service import ingest
from shared.news import NewsArticle as IncomingArticle

RSS = b"""<?xml version="1.0"?>
<rss xmlns:dc="http://purl.org/dc/elements/1.1/" version="2.0"><channel>
<item><title>Assembly debates national budget</title>
<link>https://punchng.com/assembly-budget/?utm_source=rss&amp;utm_medium=web</link>
<guid>story-1</guid><pubDate>Mon, 02 Nov 2026 17:00:00 +0000</pubDate>
<dc:creator>Punch Newspapers</dc:creator><description><![CDATA[
<p>Lawmakers considered the budget proposal.</p>
Read More: https://punchng.com/assembly-budget/
]]></description></item></channel></rss>"""


def test_rss_parser_preserves_provenance_and_removes_tracking():
    client = httpx.Client(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, content=RSS))
    )
    adapter = RSSFeedAdapter(
        source_name="Punch Newspapers",
        allowed_domains={"punchng.com"},
        feeds={"politics": "https://rss.punchng.com/v1/category/politics"},
        client=client,
    )
    articles = list(adapter.fetch())
    assert len(articles) == 1
    assert articles[0].original_url == "https://punchng.com/assembly-budget"
    assert articles[0].content == "Lawmakers considered the budget proposal."
    assert articles[0].category == "politics"
    assert articles[0].published_at == datetime(2026, 11, 2, 17, tzinfo=UTC)
    assert articles[0].metadata["feed_url"].startswith("https://rss.punchng.com/")


def test_one_failed_feed_does_not_stop_other_feeds():
    def handler(request):
        if "failed" in str(request.url):
            return httpx.Response(503)
        return httpx.Response(200, content=RSS)

    adapter = RSSFeedAdapter(
        source_name="Punch Newspapers",
        allowed_domains={"punchng.com"},
        feeds={
            "failed": "https://rss.punchng.com/failed",
            "politics": "https://rss.punchng.com/politics",
        },
        retry_limit=2,
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    assert len(list(adapter.fetch())) == 1
    assert len(adapter.failures) == 1
    assert adapter.failures[0].error_type == "HTTPStatusError"


class FakeAdapter:
    source_name = "Punch Newspapers"
    failures = []

    def fetch(self, *, limit=None):
        articles = [
            IncomingArticle(
                external_id="external-1",
                title="National Assembly debates a budget",
                content="Lawmakers and the minister discussed the proposed bill.",
                source_name=self.source_name,
                original_url="https://punchng.com/example",
                category="politics",
                published_at=datetime(2026, 11, 2, tzinfo=UTC),
            )
        ]
        return iter(articles[:limit])


class FakeModelService:
    def classify(self, text):
        return {
            "predicted_category": "politics",
            "model_id": "fixture-model",
            "model_version": "1.0",
            "score_type": "decision_function",
            "scores": [
                {"category": "politics", "value": 0.4},
                {"category": "business", "value": -0.2},
            ],
        }


def test_ingestion_persists_classification_and_is_incremental():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as session:
        first = ingest(session, FakeAdapter(), FakeModelService(), limit=10)
        second = ingest(session, FakeAdapter(), FakeModelService(), limit=10)
        assert first.inserted_count == 1
        assert second.inserted_count == 0
        assert second.duplicate_count == 1
        article = session.scalar(select(NewsArticle))
        assert article is not None
        assert article.content == ""
        assert article.excerpt.startswith("Lawmakers")
        assert article.source_category == "politics"
        prediction = session.scalar(select(ClassificationPrediction))
        assert prediction.model_version == "1.0"
        assert prediction.score_type == "decision_function"
        assert session.scalar(select(func.count()).select_from(IngestionFailure)) == 0
