import logging
import feedparser
import requests
from datetime import datetime, timezone
from typing import List

from config import RSS_FEEDS, RSS_FETCH_LIMIT, REDDIT_RSS_FEEDS, REDDIT_RSS_FETCH_LIMIT
from models import Article

logger = logging.getLogger(__name__)

HEADERS = {"User-Agent": "ai-news-agent/1.0"}


def _fetch_feed(feed_url: str, source: str, limit: int) -> List[Article]:
    """抓取單一 RSS feed，回傳 List[Article]。"""
    articles = []
    try:
        # 先用 requests 抓原始內容再交給 feedparser，
        # 可繞過部分 feed（如 Anthropic）的 XML encoding 問題
        resp = requests.get(feed_url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        feed = feedparser.parse(resp.content)

        if feed.bozo and not feed.entries:
            logger.error(f"RSS parse error ({feed_url}): {feed.bozo_exception}")
            return []

        for entry in feed.entries[:limit]:
            url = entry.get("link", "")
            if not url:
                continue

            summary = entry.get("summary", "") or ""
            if len(summary) > 500:
                summary = summary[:500] + "..."

            articles.append(Article(
                title=entry.get("title", ""),
                url=url,
                summary=summary,
                source=source,
                score=0,
                fetched_at=datetime.now(timezone.utc).isoformat(),
            ))

    except Exception as e:
        logger.error(f"RSS collector error ({feed_url}): {e}")

    return articles


def fetch() -> List[Article]:
    articles: List[Article] = []

    for feed_url in RSS_FEEDS:
        results = _fetch_feed(feed_url, "rss", RSS_FETCH_LIMIT)
        articles.extend(results)
        if results:
            logger.info(f"RSS ({feed_url}): {len(results)} articles")

    for feed_url in REDDIT_RSS_FEEDS:
        results = _fetch_feed(feed_url, "reddit_rss", REDDIT_RSS_FETCH_LIMIT)
        articles.extend(results)
        if results:
            logger.info(f"Reddit RSS ({feed_url}): {len(results)} articles")

    logger.info(f"RSS total: {len(articles)} articles")
    return articles
