"""Extend schema for news ingestion and administration.

Revision ID: 0002_news_ingestion
Revises: 0001_phase1
"""

import sqlalchemy as sa
from alembic import op

revision = "0002_news_ingestion"
down_revision = "0001_phase1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "roles",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(40), nullable=False),
        sa.Column("description", sa.String(250)),
        sa.UniqueConstraint("name"),
    )
    op.create_index("ix_roles_name", "roles", ["name"])
    with op.batch_alter_table("users") as batch:
        batch.add_column(sa.Column("password_hash", sa.String(255)))
        batch.add_column(sa.Column("updated_at", sa.DateTime(timezone=True)))
    op.execute("UPDATE users SET updated_at = created_at WHERE updated_at IS NULL")
    op.create_table(
        "user_roles",
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "role_id",
            sa.String(36),
            sa.ForeignKey("roles.id", ondelete="CASCADE"),
            primary_key=True,
        ),
    )

    with op.batch_alter_table("data_sources") as batch:
        batch.add_column(sa.Column("slug", sa.String(80)))
        batch.add_column(sa.Column("feed_url", sa.String(2048)))
        batch.add_column(sa.Column("terms_url", sa.String(2048)))
        batch.add_column(
            sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False)
        )
        batch.add_column(sa.Column("last_success_at", sa.DateTime(timezone=True)))
        batch.add_column(sa.Column("created_at", sa.DateTime(timezone=True)))
        batch.add_column(sa.Column("updated_at", sa.DateTime(timezone=True)))
        batch.create_unique_constraint("uq_data_sources_slug", ["slug"])
        batch.create_index("ix_data_sources_slug", ["slug"])
        batch.create_index("ix_data_sources_is_active", ["is_active"])
    op.execute(
        "UPDATE data_sources SET created_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP"
    )

    with op.batch_alter_table("news_articles") as batch:
        batch.add_column(sa.Column("admin_category_id", sa.String(36)))
        batch.add_column(sa.Column("source_external_id", sa.String(512)))
        batch.add_column(sa.Column("excerpt", sa.Text()))
        batch.add_column(sa.Column("author", sa.String(250)))
        batch.add_column(sa.Column("source_category", sa.String(120)))
        batch.add_column(sa.Column("language", sa.String(12), server_default="en", nullable=False))
        batch.add_column(sa.Column("image_url", sa.String(2048)))
        batch.add_column(sa.Column("source_metadata", sa.JSON()))
        batch.add_column(sa.Column("updated_at", sa.DateTime(timezone=True)))
        batch.add_column(sa.Column("deleted_at", sa.DateTime(timezone=True)))
        batch.create_foreign_key(
            "fk_news_articles_admin_category", "article_categories", ["admin_category_id"], ["id"]
        )
        batch.create_unique_constraint(
            "uq_article_source_external", ["source_id", "source_external_id"]
        )
        batch.create_index("ix_news_articles_admin_category_id", ["admin_category_id"])
        batch.create_index("ix_news_articles_deleted_at", ["deleted_at"])
    op.execute("UPDATE news_articles SET updated_at = collected_at WHERE updated_at IS NULL")

    with op.batch_alter_table("classification_predictions") as batch:
        batch.add_column(sa.Column("model_version", sa.String(80)))
        batch.add_column(sa.Column("scores", sa.JSON()))
        batch.add_column(sa.Column("input_hash", sa.String(64)))
        batch.add_column(
            sa.Column("is_current", sa.Boolean(), server_default=sa.true(), nullable=False)
        )
        batch.add_column(sa.Column("corrected_category", sa.String(80)))
        batch.add_column(sa.Column("reviewed_at", sa.DateTime(timezone=True)))
        batch.add_column(sa.Column("reviewed_by", sa.String(160)))
        batch.create_index("ix_classification_predictions_input_hash", ["input_hash"])
        batch.create_index("ix_classification_predictions_is_current", ["is_current"])

    op.create_table(
        "user_preferences",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("categories", sa.JSON()),
        sa.Column("sources", sa.JSON()),
        sa.Column("conversation_retention_days", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_user_preferences_user_id", "user_preferences", ["user_id"])
    op.create_table(
        "ingestion_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("source_id", sa.String(36), sa.ForeignKey("data_sources.id"), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("requested_limit", sa.Integer()),
        sa.Column("fetched_count", sa.Integer(), nullable=False),
        sa.Column("inserted_count", sa.Integer(), nullable=False),
        sa.Column("duplicate_count", sa.Integer(), nullable=False),
        sa.Column("failed_count", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_ingestion_runs_source_id", "ingestion_runs", ["source_id"])
    op.create_index("ix_ingestion_runs_status", "ingestion_runs", ["status"])
    op.create_index("ix_ingestion_runs_started_at", "ingestion_runs", ["started_at"])
    op.create_table(
        "ingestion_failures",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "run_id",
            sa.String(36),
            sa.ForeignKey("ingestion_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("stage", sa.String(50), nullable=False),
        sa.Column("reference", sa.String(512)),
        sa.Column("error_type", sa.String(120), nullable=False),
        sa.Column("message", sa.String(1000), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_ingestion_failures_run_id", "ingestion_failures", ["run_id"])
    op.create_table(
        "administrative_audit_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("actor", sa.String(160), nullable=False),
        sa.Column("action", sa.String(120), nullable=False),
        sa.Column("target_type", sa.String(80), nullable=False),
        sa.Column("target_id", sa.String(80)),
        sa.Column("details", sa.JSON()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_audit_actor", "administrative_audit_logs", ["actor"])
    op.create_index("ix_audit_action", "administrative_audit_logs", ["action"])
    op.create_index("ix_audit_target", "administrative_audit_logs", ["target_id"])
    op.create_index("ix_audit_created", "administrative_audit_logs", ["created_at"])
    op.create_table(
        "retrieval_metadata",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "article_id",
            sa.String(36),
            sa.ForeignKey("news_articles.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("text_hash", sa.String(64), nullable=False),
        sa.Column("indexed_at", sa.DateTime(timezone=True)),
        sa.Column("index_version", sa.String(80)),
    )
    op.create_index("ix_retrieval_article", "retrieval_metadata", ["article_id"])
    op.create_index("ix_retrieval_hash", "retrieval_metadata", ["text_hash"])


def downgrade() -> None:
    op.drop_table("retrieval_metadata")
    op.drop_table("administrative_audit_logs")
    op.drop_table("ingestion_failures")
    op.drop_table("ingestion_runs")
    op.drop_table("user_preferences")
    with op.batch_alter_table("classification_predictions") as batch:
        batch.drop_index("ix_classification_predictions_is_current")
        batch.drop_index("ix_classification_predictions_input_hash")
        for column in (
            "reviewed_by",
            "reviewed_at",
            "corrected_category",
            "is_current",
            "input_hash",
            "scores",
            "model_version",
        ):
            batch.drop_column(column)
    with op.batch_alter_table("news_articles") as batch:
        batch.drop_index("ix_news_articles_deleted_at")
        batch.drop_index("ix_news_articles_admin_category_id")
        batch.drop_constraint("uq_article_source_external", type_="unique")
        batch.drop_constraint("fk_news_articles_admin_category", type_="foreignkey")
        for column in (
            "deleted_at",
            "updated_at",
            "source_metadata",
            "image_url",
            "language",
            "source_category",
            "author",
            "excerpt",
            "source_external_id",
            "admin_category_id",
        ):
            batch.drop_column(column)
    with op.batch_alter_table("data_sources") as batch:
        batch.drop_index("ix_data_sources_is_active")
        batch.drop_index("ix_data_sources_slug")
        batch.drop_constraint("uq_data_sources_slug", type_="unique")
        for column in (
            "updated_at",
            "created_at",
            "last_success_at",
            "is_active",
            "terms_url",
            "feed_url",
            "slug",
        ):
            batch.drop_column(column)
    op.drop_table("user_roles")
    with op.batch_alter_table("users") as batch:
        batch.drop_column("updated_at")
        batch.drop_column("password_hash")
    op.drop_table("roles")
