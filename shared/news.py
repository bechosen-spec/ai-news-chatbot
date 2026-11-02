"""Source-neutral news ingestion contracts without ML/runtime dependencies."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable
from dataclasses import asdict, dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class NewsSourceDescriptor:
    slug: str
    name: str
    base_url: str
    feed_url: str | None
    terms_url: str | None
    ingestion_method: str = "rss"


@dataclass(frozen=True)
class NewsArticle:
    external_id: str
    title: str
    content: str
    source_name: str
    original_url: str
    published_at: datetime | None = None
    collected_at: datetime | None = None
    language: str = "en"
    category: str | None = None
    author: str | None = None
    image_url: str | None = None
    metadata: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class NewsSourceAdapter(ABC):
    """Implemented only for sources with verified, permitted APIs or feeds."""

    descriptor: NewsSourceDescriptor

    @abstractmethod
    def fetch(self, *, limit: int | None = None) -> Iterable[NewsArticle]:
        """Yield normalized articles while retaining source provenance."""
