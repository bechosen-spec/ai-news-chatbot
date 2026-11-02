"""Strict RSS 2.0 adapter for explicitly verified publisher feeds."""

from __future__ import annotations

import hashlib
import html
import logging
import re
import time
from collections import deque
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import httpx
from defusedxml import ElementTree

from shared.news import NewsArticle, NewsSourceAdapter, NewsSourceDescriptor

LOGGER = logging.getLogger(__name__)
TRACKING_PARAMETERS = {"utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content"}
DC_CREATOR = "{http://purl.org/dc/elements/1.1/}creator"


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def plain_text(value: str, max_characters: int) -> str:
    parser = _TextExtractor()
    parser.feed(html.unescape(value or ""))
    text = re.sub(r"\s+", " ", " ".join(parser.parts)).strip()
    text = re.sub(r"\s*Read More:\s*https?://\S+\s*$", "", text, flags=re.IGNORECASE)
    return text[:max_characters].rstrip()


def canonicalize_url(value: str) -> str:
    parsed = urlsplit(value.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("Article URL must use HTTP(S)")
    query = urlencode(
        [
            (key, item)
            for key, item in parse_qsl(parsed.query)
            if key.lower() not in TRACKING_PARAMETERS
        ]
    )
    return urlunsplit(
        (parsed.scheme.lower(), parsed.netloc.lower(), parsed.path.rstrip("/"), query, "")
    )


def parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    parsed = parsedate_to_datetime(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


@dataclass(frozen=True)
class FeedFailure:
    feed_url: str
    error_type: str
    message: str


class RSSFeedAdapter(NewsSourceAdapter):
    def __init__(
        self,
        *,
        descriptor: NewsSourceDescriptor,
        allowed_domains: set[str],
        feeds: dict[str, str],
        timeout_seconds: float = 15,
        retry_limit: int = 3,
        excerpt_max_characters: int = 1_500,
        client: httpx.Client | None = None,
    ) -> None:
        self.descriptor = descriptor
        self.source_name = descriptor.name
        self.allowed_domains = allowed_domains
        self.feeds = feeds
        self.timeout_seconds = timeout_seconds
        self.retry_limit = retry_limit
        self.excerpt_max_characters = excerpt_max_characters
        self.client = client
        self.failures: list[FeedFailure] = []

    def _download(self, url: str) -> bytes:
        client = self.client or httpx.Client(
            timeout=self.timeout_seconds,
            follow_redirects=True,
            headers={"User-Agent": "ai-news-chatbot/0.2 (+research news aggregator)"},
        )
        close_client = self.client is None
        try:
            last_error: Exception | None = None
            for attempt in range(self.retry_limit):
                try:
                    response = client.get(url)
                    response.raise_for_status()
                    if len(response.content) > 5_000_000:
                        raise ValueError("RSS response exceeded 5 MB safety limit")
                    return response.content
                except (httpx.HTTPError, ValueError) as error:
                    last_error = error
                    if attempt + 1 < self.retry_limit:
                        time.sleep(0.25 * (2**attempt))
            assert last_error is not None
            raise last_error
        finally:
            if close_client:
                client.close()

    def _parse(self, xml: bytes, source_category: str, feed_url: str) -> list[NewsArticle]:
        root = ElementTree.fromstring(xml)
        if root.tag != "rss":
            raise ValueError("Expected an RSS 2.0 document")
        articles: list[NewsArticle] = []
        for item in root.findall("./channel/item"):
            title = plain_text(item.findtext("title") or "", 1_000)
            raw_url = item.findtext("link") or ""
            if not title or not raw_url:
                continue
            canonical_url = canonicalize_url(raw_url)
            if urlsplit(canonical_url).hostname not in self.allowed_domains:
                raise ValueError("RSS item linked to an unexpected domain")
            excerpt = plain_text(item.findtext("description") or "", self.excerpt_max_characters)
            guid = (item.findtext("guid") or canonical_url).strip()
            enclosure = item.find("enclosure")
            image_url = enclosure.get("url") if enclosure is not None else None
            articles.append(
                NewsArticle(
                    external_id=hashlib.sha256(guid.encode()).hexdigest(),
                    title=title,
                    content=excerpt,
                    source_name=self.source_name,
                    original_url=canonical_url,
                    published_at=parse_date(item.findtext("pubDate")),
                    collected_at=datetime.now(UTC),
                    category=source_category,
                    author=plain_text(item.findtext(DC_CREATOR) or "", 250) or None,
                    image_url=image_url,
                    metadata={"feed_url": feed_url, "rss_guid": guid},
                )
            )
        return articles

    def fetch(self, *, limit: int | None = None):
        self.failures = []
        seen: set[str] = set()
        yielded = 0
        buckets: list[deque[NewsArticle]] = []
        for category, feed_url in self.feeds.items():
            try:
                articles = self._parse(self._download(feed_url), category, feed_url)
            except Exception as error:
                LOGGER.warning("RSS feed unavailable source=%s feed=%s", self.source_name, feed_url)
                self.failures.append(FeedFailure(feed_url, type(error).__name__, str(error)[:500]))
                continue
            buckets.append(deque(articles))
        while buckets:
            remaining: list[deque[NewsArticle]] = []
            for bucket in buckets:
                if not bucket:
                    continue
                article = bucket.popleft()
                if article.original_url in seen:
                    if bucket:
                        remaining.append(bucket)
                    continue
                seen.add(article.original_url)
                yield article
                yielded += 1
                if limit is not None and yielded >= limit:
                    return
                if bucket:
                    remaining.append(bucket)
            buckets = remaining


PUNCH_FEEDS = {
    "latest": "https://rss.punchng.com/v1/category/latest_news",
}


def punch_adapter(**options) -> RSSFeedAdapter:
    return RSSFeedAdapter(
        descriptor=NewsSourceDescriptor(
            slug="punch",
            name="Punch Newspapers",
            base_url="https://punchng.com",
            feed_url="https://rss.punchng.com/",
            terms_url="https://rss.punchng.com/",
        ),
        allowed_domains={"punchng.com", "www.punchng.com"},
        feeds=PUNCH_FEEDS,
        **options,
    )
