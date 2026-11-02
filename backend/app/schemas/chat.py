from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=2, max_length=2_000)
    conversation_id: str | None = None
    category: str | None = Field(default=None, pattern=r"^[a-z][a-z0-9_-]{1,79}$")
    source: str | None = Field(default=None, pattern=r"^[a-z][a-z0-9_-]{1,79}$")
    published_after: datetime | None = None
    published_before: datetime | None = None


class CitationResponse(BaseModel):
    citation_id: str
    article_id: str
    title: str
    publisher: str
    source_slug: str | None
    url: HttpUrl
    published_at: datetime | None
    excerpt: str
    category: str | None


class DiversityResponse(BaseModel):
    unique_sources: int
    source_diversity_ratio: float
    candidate_count: int


class ChatResponse(BaseModel):
    conversation_id: str
    message_id: str
    answer: str
    citations: list[CitationResponse]
    limitations: list[str]
    status: str
    diversity: DiversityResponse


class MessageResponse(BaseModel):
    id: str
    role: str
    content: str
    citations: list[dict] | None
    status: str
    created_at: datetime


class ConversationSummary(BaseModel):
    id: str
    title: str | None
    created_at: datetime
    updated_at: datetime


class ConversationDetail(ConversationSummary):
    messages: list[MessageResponse]


class ChatHealthResponse(BaseModel):
    status: str
    provider: str
    provider_configured: bool
    authentication_configured: bool
    indexed_articles: int
