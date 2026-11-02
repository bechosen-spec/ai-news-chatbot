"""Add retrieval index fields and owner-scoped persistent chat.

Revision ID: 0003_rag_chat
Revises: 0002_news_ingestion
"""

import sqlalchemy as sa
from alembic import op

revision = "0003_rag_chat"
down_revision = "0002_news_ingestion"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("chat_conversations") as batch:
        batch.add_column(sa.Column("owner_subject", sa.String(255)))
        batch.add_column(sa.Column("updated_at", sa.DateTime(timezone=True)))
        batch.add_column(sa.Column("deleted_at", sa.DateTime(timezone=True)))
        batch.create_index("ix_chat_conversations_owner_subject", ["owner_subject"])
        batch.create_index("ix_chat_conversations_deleted_at", ["deleted_at"])
    op.execute("UPDATE chat_conversations SET updated_at = created_at WHERE updated_at IS NULL")
    with op.batch_alter_table("chat_conversations") as batch:
        batch.alter_column("updated_at", existing_type=sa.DateTime(timezone=True), nullable=False)
    with op.batch_alter_table("chat_messages") as batch:
        batch.add_column(sa.Column("citations", sa.JSON()))
        batch.add_column(sa.Column("message_metadata", sa.JSON()))
        batch.add_column(
            sa.Column("status", sa.String(40), server_default="complete", nullable=False)
        )
    with op.batch_alter_table("retrieval_metadata") as batch:
        batch.add_column(sa.Column("term_frequencies", sa.JSON()))
        batch.add_column(sa.Column("title_term_frequencies", sa.JSON()))
        batch.add_column(
            sa.Column("document_length", sa.Integer(), server_default="0", nullable=False)
        )


def downgrade() -> None:
    with op.batch_alter_table("retrieval_metadata") as batch:
        batch.drop_column("document_length")
        batch.drop_column("title_term_frequencies")
        batch.drop_column("term_frequencies")
    with op.batch_alter_table("chat_messages") as batch:
        batch.drop_column("status")
        batch.drop_column("message_metadata")
        batch.drop_column("citations")
    with op.batch_alter_table("chat_conversations") as batch:
        batch.drop_index("ix_chat_conversations_deleted_at")
        batch.drop_index("ix_chat_conversations_owner_subject")
        batch.drop_column("deleted_at")
        batch.drop_column("updated_at")
        batch.drop_column("owner_subject")
