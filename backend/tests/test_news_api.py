from datetime import UTC, datetime

from backend.app.db.base import Base
from backend.app.db.models import (
    ArticleCategory,
    ClassificationPrediction,
    DataSource,
    NewsArticle,
)


def seed_news(client):
    Base.metadata.create_all(client.app.state.engine)
    with client.app.state.session_factory() as session:
        source = DataSource(
            name="Punch Newspapers",
            slug="punch",
            base_url="https://punchng.com",
            ingestion_method="rss",
            is_active=True,
        )
        politics = ArticleCategory(slug="politics", display_name="Politics")
        tech = ArticleCategory(slug="tech", display_name="Technology")
        article = NewsArticle(
            source=source,
            category=politics,
            source_external_id="news-api-1",
            title="Assembly debates digital economy bill",
            content="",
            excerpt="Lawmakers debated technology policy in Abuja.",
            source_category="politics",
            original_url="https://punchng.com/digital-economy-bill",
            content_hash="f" * 64,
            published_at=datetime(2026, 11, 2, 12, tzinfo=UTC),
        )
        article.predictions.append(
            ClassificationPrediction(
                model_id="fixture",
                model_version="1",
                predicted_category="politics",
                score_type="decision_function",
                top_score=0.5,
                is_current=True,
            )
        )
        session.add_all([source, politics, tech, article])
        session.commit()
        return article.id


def test_news_listing_search_filters_and_detail(client):
    article_id = seed_news(client)
    listing = client.get("/api/v1/news", params={"category": "politics", "source": "punch"})
    assert listing.status_code == 200
    assert listing.json()["total"] == 1
    assert listing.json()["items"][0]["publisher"] == "Punch Newspapers"
    assert "content" not in listing.json()["items"][0]

    search = client.get("/api/v1/news/search", params={"q": "technology"})
    assert search.status_code == 200
    assert search.json()["total"] == 1

    detail = client.get(f"/api/v1/news/{article_id}")
    assert detail.status_code == 200
    assert detail.json()["classification"]["score_type"] == "decision_function"
    assert detail.json()["published_at"].endswith("Z")
    assert "full article" in detail.json()["content_republication_notice"].lower()


def test_admin_authorization_correction_and_soft_delete(client):
    article_id = seed_news(client)
    assert (
        client.patch(f"/api/v1/admin/news/{article_id}", json={"category_slug": "tech"}).status_code
        == 401
    )
    headers = {"X-Admin-Key": "test-admin-key"}
    update = client.patch(
        f"/api/v1/admin/news/{article_id}",
        headers=headers,
        json={"category_slug": "tech"},
    )
    assert update.status_code == 200
    detail = client.get(f"/api/v1/news/{article_id}")
    assert detail.json()["category"] == "tech"
    assert detail.json()["classification"]["predicted_category"] == "politics"
    assert detail.json()["classification"]["administrator_corrected"] is True

    deleted = client.delete(f"/api/v1/admin/news/{article_id}", headers=headers)
    assert deleted.status_code == 204
    assert client.get(f"/api/v1/news/{article_id}").status_code == 404
    assert client.get("/api/v1/news").json()["total"] == 0


def test_news_pagination_and_search_validation(client):
    seed_news(client)
    assert client.get("/api/v1/news", params={"page_size": 101}).status_code == 422
    assert client.get("/api/v1/news/search", params={"q": "x"}).status_code == 422
