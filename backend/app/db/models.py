"""Normalized Phase 1 database foundation."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base


def new_id() -> str:
    return str(uuid.uuid4())


def now_utc() -> datetime:
    return datetime.now(UTC)


user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", String(36), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", String(36), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
)


class Role(Base):
    __tablename__ = "roles"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(String(250))
    users: Mapped[list[User]] = relationship(secondary=user_roles, back_populates="roles")


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    display_name: Mapped[str | None] = mapped_column(String(120))
    password_hash: Mapped[str | None] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now_utc, onupdate=now_utc
    )
    conversations: Mapped[list[ChatConversation]] = relationship(back_populates="user")
    roles: Mapped[list[Role]] = relationship(secondary=user_roles, back_populates="users")
    preferences: Mapped[UserPreference | None] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class DataSource(Base):
    __tablename__ = "data_sources"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(160), unique=True)
    slug: Mapped[str | None] = mapped_column(String(80), unique=True, index=True)
    base_url: Mapped[str] = mapped_column(String(2048))
    ingestion_method: Mapped[str] = mapped_column(String(40))
    feed_url: Mapped[str | None] = mapped_column(String(2048))
    terms_url: Mapped[str | None] = mapped_column(String(2048))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now_utc, onupdate=now_utc
    )
    articles: Mapped[list[NewsArticle]] = relationship(back_populates="source")
    ingestion_runs: Mapped[list[IngestionRun]] = relationship(back_populates="source")


class ArticleCategory(Base):
    __tablename__ = "article_categories"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(120))
    articles: Mapped[list[NewsArticle]] = relationship(
        back_populates="category", foreign_keys="NewsArticle.category_id"
    )


class NewsArticle(Base):
    __tablename__ = "news_articles"
    __table_args__ = (
        Index("ix_articles_published_at", "published_at"),
        UniqueConstraint("source_id", "source_external_id", name="uq_article_source_external"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    source_id: Mapped[str] = mapped_column(ForeignKey("data_sources.id"), index=True)
    category_id: Mapped[str | None] = mapped_column(ForeignKey("article_categories.id"), index=True)
    admin_category_id: Mapped[str | None] = mapped_column(
        ForeignKey("article_categories.id"), index=True
    )
    source_external_id: Mapped[str | None] = mapped_column(String(512))
    title: Mapped[str] = mapped_column(String(1000))
    content: Mapped[str] = mapped_column(Text)
    excerpt: Mapped[str | None] = mapped_column(Text)
    author: Mapped[str | None] = mapped_column(String(250))
    source_category: Mapped[str | None] = mapped_column(String(120))
    language: Mapped[str] = mapped_column(String(12), default="en")
    image_url: Mapped[str | None] = mapped_column(String(2048))
    source_metadata: Mapped[dict | None] = mapped_column(JSON)
    original_url: Mapped[str] = mapped_column(String(2048), unique=True)
    content_hash: Mapped[str] = mapped_column(String(64), index=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now_utc, onupdate=now_utc
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    source: Mapped[DataSource] = relationship(back_populates="articles")
    category: Mapped[ArticleCategory | None] = relationship(
        back_populates="articles", foreign_keys=[category_id]
    )
    admin_category: Mapped[ArticleCategory | None] = relationship(foreign_keys=[admin_category_id])
    predictions: Mapped[list[ClassificationPrediction]] = relationship(
        back_populates="article", cascade="all, delete-orphan"
    )
    retrieval_metadata: Mapped[RetrievalMetadata | None] = relationship(
        back_populates="article", cascade="all, delete-orphan"
    )


class ChatConversation(Base):
    __tablename__ = "chat_conversations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str | None] = mapped_column(String(250))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    user: Mapped[User | None] = relationship(back_populates="conversations")
    messages: Mapped[list[ChatMessage]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan"
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    conversation_id: Mapped[str] = mapped_column(
        ForeignKey("chat_conversations.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    conversation: Mapped[ChatConversation] = relationship(back_populates="messages")


class ClassificationPrediction(Base):
    __tablename__ = "classification_predictions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    article_id: Mapped[str | None] = mapped_column(ForeignKey("news_articles.id"), index=True)
    model_id: Mapped[str] = mapped_column(String(160), index=True)
    model_version: Mapped[str | None] = mapped_column(String(80))
    predicted_category: Mapped[str] = mapped_column(String(80), index=True)
    score_type: Mapped[str] = mapped_column(String(40))
    top_score: Mapped[float | None] = mapped_column(Float)
    scores: Mapped[list[dict] | None] = mapped_column(JSON)
    input_hash: Mapped[str | None] = mapped_column(String(64), index=True)
    is_current: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    corrected_category: Mapped[str | None] = mapped_column(String(80))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reviewed_by: Mapped[str | None] = mapped_column(String(160))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    article: Mapped[NewsArticle | None] = relationship(back_populates="predictions")
    feedback: Mapped[list[UserFeedback]] = relationship(back_populates="prediction")


class UserFeedback(Base):
    __tablename__ = "user_feedback"
    __table_args__ = (
        UniqueConstraint("user_id", "prediction_id", name="uq_feedback_user_prediction"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), index=True)
    prediction_id: Mapped[str] = mapped_column(
        ForeignKey("classification_predictions.id"), index=True
    )
    is_correct: Mapped[bool | None] = mapped_column(Boolean)
    corrected_category: Mapped[str | None] = mapped_column(String(80))
    comment: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    prediction: Mapped[ClassificationPrediction] = relationship(back_populates="feedback")


class UserPreference(Base):
    __tablename__ = "user_preferences"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True
    )
    categories: Mapped[list[str] | None] = mapped_column(JSON)
    sources: Mapped[list[str] | None] = mapped_column(JSON)
    conversation_retention_days: Mapped[int] = mapped_column(Integer, default=90)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now_utc, onupdate=now_utc
    )
    user: Mapped[User] = relationship(back_populates="preferences")


class IngestionRun(Base):
    __tablename__ = "ingestion_runs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    source_id: Mapped[str] = mapped_column(ForeignKey("data_sources.id"), index=True)
    status: Mapped[str] = mapped_column(String(30), index=True)
    requested_limit: Mapped[int | None] = mapped_column(Integer)
    fetched_count: Mapped[int] = mapped_column(Integer, default=0)
    inserted_count: Mapped[int] = mapped_column(Integer, default=0)
    duplicate_count: Mapped[int] = mapped_column(Integer, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now_utc, index=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source: Mapped[DataSource] = relationship(back_populates="ingestion_runs")
    failures: Mapped[list[IngestionFailure]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )


class IngestionFailure(Base):
    __tablename__ = "ingestion_failures"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    run_id: Mapped[str] = mapped_column(
        ForeignKey("ingestion_runs.id", ondelete="CASCADE"), index=True
    )
    stage: Mapped[str] = mapped_column(String(50))
    reference: Mapped[str | None] = mapped_column(String(512))
    error_type: Mapped[str] = mapped_column(String(120))
    message: Mapped[str] = mapped_column(String(1000))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    run: Mapped[IngestionRun] = relationship(back_populates="failures")


class AdministrativeAuditLog(Base):
    __tablename__ = "administrative_audit_logs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    actor: Mapped[str] = mapped_column(String(160), index=True)
    action: Mapped[str] = mapped_column(String(120), index=True)
    target_type: Mapped[str] = mapped_column(String(80))
    target_id: Mapped[str | None] = mapped_column(String(80), index=True)
    details: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now_utc, index=True
    )


class RetrievalMetadata(Base):
    __tablename__ = "retrieval_metadata"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    article_id: Mapped[str] = mapped_column(
        ForeignKey("news_articles.id", ondelete="CASCADE"), unique=True, index=True
    )
    text_hash: Mapped[str] = mapped_column(String(64), index=True)
    indexed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    index_version: Mapped[str | None] = mapped_column(String(80))
    article: Mapped[NewsArticle] = relationship(back_populates="retrieval_metadata")
