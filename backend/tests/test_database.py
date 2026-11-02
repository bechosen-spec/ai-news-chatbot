import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.db.base import Base
from backend.app.db.models import ArticleCategory, DataSource, NewsArticle, User


def test_models_and_constraints_initialize():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        source = DataSource(name="Example", base_url="https://example.com", ingestion_method="rss")
        category = ArticleCategory(slug="politics", display_name="Politics")
        article = NewsArticle(
            source=source,
            category=category,
            title="A title",
            content="Article body",
            original_url="https://example.com/a",
            content_hash="a" * 64,
        )
        session.add_all([source, category, article])
        session.commit()
        assert session.scalar(select(NewsArticle)).source.name == "Example"

        session.add(User(email="reader@example.com"))
        session.commit()
        session.add(User(email="reader@example.com"))
        with pytest.raises(IntegrityError):
            session.commit()
