"""Normalized Phase 1 database foundation."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base


def new_id() -> str:
    return str(uuid.uuid4())


def now_utc() -> datetime:
    return datetime.now(UTC)


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    display_name: Mapped[str | None] = mapped_column(String(120))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    conversations: Mapped[list[ChatConversation]] = relationship(back_populates="user")


class DataSource(Base):
    __tablename__ = "data_sources"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(160), unique=True)
    base_url: Mapped[str] = mapped_column(String(2048))
    ingestion_method: Mapped[str] = mapped_column(String(40))
    articles: Mapped[list[NewsArticle]] = relationship(back_populates="source")


class ArticleCategory(Base):
    __tablename__ = "article_categories"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(120))
    articles: Mapped[list[NewsArticle]] = relationship(back_populates="category")


class NewsArticle(Base):
    __tablename__ = "news_articles"
    __table_args__ = (Index("ix_articles_published_at", "published_at"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    source_id: Mapped[str] = mapped_column(ForeignKey("data_sources.id"), index=True)
    category_id: Mapped[str | None] = mapped_column(ForeignKey("article_categories.id"), index=True)
    title: Mapped[str] = mapped_column(String(1000))
    content: Mapped[str] = mapped_column(Text)
    original_url: Mapped[str] = mapped_column(String(2048), unique=True)
    content_hash: Mapped[str] = mapped_column(String(64), index=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    source: Mapped[DataSource] = relationship(back_populates="articles")
    category: Mapped[ArticleCategory | None] = relationship(back_populates="articles")
    predictions: Mapped[list[ClassificationPrediction]] = relationship(back_populates="article")


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
    predicted_category: Mapped[str] = mapped_column(String(80), index=True)
    score_type: Mapped[str] = mapped_column(String(40))
    top_score: Mapped[float | None] = mapped_column(Float)
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
