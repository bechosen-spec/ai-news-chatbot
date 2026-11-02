"""Small, deterministic text normalization shared by indexing and retrieval."""

import re
from collections import Counter

TOKEN_RE = re.compile(r"[a-z0-9]+(?:'[a-z0-9]+)?")
STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "did",
    "do",
    "for",
    "from",
    "has",
    "have",
    "how",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "this",
    "to",
    "was",
    "were",
    "what",
    "when",
    "where",
    "which",
    "who",
    "why",
    "with",
}


def normalize_tokens(value: str, *, limit: int = 256) -> list[str]:
    tokens = TOKEN_RE.findall(value.casefold())
    meaningful = [token for token in tokens if token not in STOP_WORDS and len(token) > 1]
    return meaningful[:limit]


def term_frequencies(value: str) -> dict[str, int]:
    return dict(Counter(normalize_tokens(value, limit=10_000)))
