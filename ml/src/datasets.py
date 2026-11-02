"""Dataset schemas, validation, splitting, and future-source adapters."""

from __future__ import annotations

import hashlib
import re
from abc import ABC, abstractmethod
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from datetime import datetime

import pandas as pd
from sklearn.model_selection import train_test_split

BBC_CATEGORIES = ("business", "entertainment", "politics", "sport", "tech")
RANDOM_SEED = 42


@dataclass(frozen=True)
class NewsArticle:
    """Source-neutral article shape for later Nigerian feed/API ingestion."""

    external_id: str
    title: str
    content: str
    source_name: str
    original_url: str
    published_at: datetime | None = None
    collected_at: datetime | None = None
    language: str = "en"
    category: str | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class NewsSourceAdapter(ABC):
    """Interface implemented only for sources with permitted APIs or feeds."""

    @abstractmethod
    def fetch(self, *, limit: int | None = None) -> Iterable[NewsArticle]:
        """Yield normalized articles while retaining provenance."""


def normalize_text(value: object) -> str:
    """Apply conservative Unicode/whitespace normalization."""
    if value is None or pd.isna(value):
        return ""
    text = str(value).replace("\u00a0", " ")
    return re.sub(r"\s+", " ", text).strip()


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def validate_frame(frame: pd.DataFrame, categories: tuple[str, ...] = BBC_CATEGORIES) -> None:
    required = {"text", "label"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Dataset is missing columns: {sorted(missing)}")
    if frame["text"].isna().any() or (frame["text"].astype(str).str.strip() == "").any():
        raise ValueError("Dataset contains missing or empty text")
    invalid = sorted(set(frame["label"]) - set(categories))
    if invalid:
        raise ValueError(f"Dataset contains invalid categories: {invalid}")


def stratified_split(
    frame: pd.DataFrame, seed: int = RANDOM_SEED
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Create deterministic 70/15/15 partitions with no exact text overlap."""
    train, remainder = train_test_split(
        frame, test_size=0.30, random_state=seed, stratify=frame["label"]
    )
    validation, test = train_test_split(
        remainder,
        test_size=0.50,
        random_state=seed,
        stratify=remainder["label"],
    )
    parts = [
        part.sort_values("article_id").reset_index(drop=True) for part in (train, validation, test)
    ]
    hashes = [set(part["content_hash"]) for part in parts]
    if any(hashes[i] & hashes[j] for i in range(3) for j in range(i + 1, 3)):
        raise RuntimeError("Content overlap detected between dataset splits")
    return tuple(parts)  # type: ignore[return-value]
