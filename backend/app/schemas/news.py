from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


def _as_utc(value: datetime | None) -> datetime | None:
    if value is not None and value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC) if value is not None else None


class ClassificationSummary(BaseModel):
    predicted_category: str
    model_id: str
    model_version: str | None
    score_type: str
    top_score: float | None
    administrator_corrected: bool


class ArticleSummary(BaseModel):
    id: str
    title: str
    excerpt: str | None
    original_url: HttpUrl
    publisher: str
    source_slug: str | None
    source_category: str | None
    category: str | None
    published_at: datetime | None
    collected_at: datetime
    image_url: HttpUrl | None

    @field_validator("published_at", "collected_at", mode="before")
    @classmethod
    def normalize_utc(cls, value):
        return _as_utc(value)


class ArticleDetail(ArticleSummary):
    author: str | None
    language: str
    classification: ClassificationSummary | None
    content_republication_notice: str = (
        "Only publisher-provided RSS metadata and excerpt are stored. "
        "Read the full article at the source."
    )


class PaginatedArticles(BaseModel):
    items: list[ArticleSummary]
    page: int
    page_size: int
    total: int
    pages: int


class CategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    slug: str
    display_name: str


class SourceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    slug: str | None
    name: str
    base_url: HttpUrl
    ingestion_method: str
    is_active: bool
    last_success_at: datetime | None

    @field_validator("last_success_at", mode="before")
    @classmethod
    def normalize_utc(cls, value):
        return _as_utc(value)


class IngestionRequest(BaseModel):
    source: Literal["punch"] = "punch"
    limit: int = Field(default=50, ge=1, le=200)


class IngestionFailureResponse(BaseModel):
    stage: str
    reference: str | None
    error_type: str
    message: str


class IngestionRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    source_id: str
    status: str
    requested_limit: int | None
    fetched_count: int
    inserted_count: int
    duplicate_count: int
    failed_count: int
    started_at: datetime
    completed_at: datetime | None
    failures: list[IngestionFailureResponse] = []

    @field_validator("started_at", "completed_at", mode="before")
    @classmethod
    def normalize_utc(cls, value):
        return _as_utc(value)


class ArticleAdminUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category_slug: str | None = Field(default=None, pattern=r"^[a-z][a-z0-9_-]{1,79}$")
    is_deleted: bool | None = None
