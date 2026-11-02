from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


def test_migration_upgrade_and_downgrade(tmp_path, monkeypatch):
    database = tmp_path / "migration.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database}")
    from backend.app.core.config import get_settings

    get_settings.cache_clear()
    config = Config("alembic.ini")
    command.upgrade(config, "head")
    tables = set(inspect(create_engine(f"sqlite:///{database}")).get_table_names())
    assert {"users", "news_articles", "chat_messages", "classification_predictions"} <= tables
    command.downgrade(config, "base")
    remaining = set(inspect(create_engine(f"sqlite:///{database}")).get_table_names())
    assert not ({"users", "news_articles"} & remaining)
    get_settings.cache_clear()
