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
    inspector = inspect(create_engine(f"sqlite:///{database}"))
    conversation_columns = {
        column["name"] for column in inspector.get_columns("chat_conversations")
    }
    retrieval_columns = {column["name"] for column in inspector.get_columns("retrieval_metadata")}
    assert {"owner_subject", "updated_at", "deleted_at"} <= conversation_columns
    assert {"term_frequencies", "document_length"} <= retrieval_columns
    command.downgrade(config, "base")
    remaining = set(inspect(create_engine(f"sqlite:///{database}")).get_table_names())
    assert not ({"users", "news_articles"} & remaining)
    get_settings.cache_clear()
