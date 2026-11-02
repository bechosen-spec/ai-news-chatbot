"""Create Phase 1 application tables."""

import sqlalchemy as sa
from alembic import op

revision = "0001_phase1"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("display_name", sa.String(120)),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_email", "users", ["email"])
    op.create_table(
        "data_sources",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(160), nullable=False, unique=True),
        sa.Column("base_url", sa.String(2048), nullable=False),
        sa.Column("ingestion_method", sa.String(40), nullable=False),
    )
    op.create_table(
        "article_categories",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("slug", sa.String(80), nullable=False, unique=True),
        sa.Column("display_name", sa.String(120), nullable=False),
    )
    op.create_index("ix_article_categories_slug", "article_categories", ["slug"])
    op.create_table(
        "chat_conversations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id")),
        sa.Column("title", sa.String(250)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_chat_conversations_user_id", "chat_conversations", ["user_id"])
    op.create_table(
        "news_articles",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("source_id", sa.String(36), sa.ForeignKey("data_sources.id"), nullable=False),
        sa.Column("category_id", sa.String(36), sa.ForeignKey("article_categories.id")),
        sa.Column("title", sa.String(1000), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("original_url", sa.String(2048), nullable=False, unique=True),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False),
    )
    for index, columns in (
        ("ix_articles_published_at", ["published_at"]),
        ("ix_news_articles_source_id", ["source_id"]),
        ("ix_news_articles_category_id", ["category_id"]),
        ("ix_news_articles_content_hash", ["content_hash"]),
    ):
        op.create_index(index, "news_articles", columns)
    op.create_table(
        "chat_messages",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "conversation_id",
            sa.String(36),
            sa.ForeignKey("chat_conversations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_chat_messages_conversation_id", "chat_messages", ["conversation_id"])
    op.create_table(
        "classification_predictions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("article_id", sa.String(36), sa.ForeignKey("news_articles.id")),
        sa.Column("model_id", sa.String(160), nullable=False),
        sa.Column("predicted_category", sa.String(80), nullable=False),
        sa.Column("score_type", sa.String(40), nullable=False),
        sa.Column("top_score", sa.Float()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    for index, columns in (
        ("ix_classification_predictions_article_id", ["article_id"]),
        ("ix_classification_predictions_model_id", ["model_id"]),
        ("ix_classification_predictions_predicted_category", ["predicted_category"]),
    ):
        op.create_index(index, "classification_predictions", columns)
    op.create_table(
        "user_feedback",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id")),
        sa.Column(
            "prediction_id",
            sa.String(36),
            sa.ForeignKey("classification_predictions.id"),
            nullable=False,
        ),
        sa.Column("is_correct", sa.Boolean()),
        sa.Column("corrected_category", sa.String(80)),
        sa.Column("comment", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "prediction_id", name="uq_feedback_user_prediction"),
    )
    op.create_index("ix_user_feedback_user_id", "user_feedback", ["user_id"])
    op.create_index("ix_user_feedback_prediction_id", "user_feedback", ["prediction_id"])


def downgrade() -> None:
    for table in (
        "user_feedback",
        "classification_predictions",
        "chat_messages",
        "news_articles",
        "chat_conversations",
        "article_categories",
        "data_sources",
        "users",
    ):
        op.drop_table(table)
