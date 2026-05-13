import logging
import re
import feedparser
import requests
from datetime import datetime, timezone
from typing import List

from config import RSS_FEEDS, RSS_FETCH_LIMIT, REDDIT_RSS_FEEDS, REDDIT_RSS_FETCH_LIMIT
from models import Article

logger = logging.getLogger(__name__)

HEADERS = {"User-Agent": "ai-news-agent/1.0"}

_REDDIT_URL_RE = re.compile(r"https?://(?:www\.)?reddit\.com")
_REDDIT_CDN_RE = re.compile(r"https?://(?:i|preview|external-preview)\.redd\.it")


def _extract_reddit_article_url(summary_html: str) -> str:
    """
    從 Reddit RSS summary HTML 提取被分享的外部文章 URL。
    Reddit 分享文的第一個非 Reddit、非 CDN 的 href 就是外部連結。
    找不到則回傳空字串（代表這是自發文）。
    """
    for href in re.findall(r'href="(https?://[^"]+)"', summary_html):
        if not _REDDIT_URL_RE.match(href) and not _REDDIT_CDN_RE.match(href):
            return href
    return ""


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


def _fetch_reddit_rss(feed_url: str, limit: int) -> List[Article]:
    """
    抓取 Reddit RSS feed。
    分享文：提取 summary HTML 裡的外部文章 URL 作為 Article.url。
    自發文（找不到外部連結）：保留 Reddit 留言頁 URL。
    """
    articles = []
    try:
        resp = requests.get(feed_url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        feed = feedparser.parse(resp.content)

        if feed.bozo and not feed.entries:
            logger.error(f"Reddit RSS parse error ({feed_url}): {feed.bozo_exception}")
            return []

        for entry in feed.entries[:limit]:
            reddit_url = entry.get("link", "")
            if not reddit_url:
                continue

            summary_html = entry.get("summary", "") or ""

            # 嘗試提取外部文章 URL；找不到則使用 Reddit 留言頁
            article_url = _extract_reddit_article_url(summary_html) or reddit_url

            # summary 用純文字版本（移除 HTML tag）
            summary = re.sub(r"<[^>]+>", " ", summary_html)
            summary = re.sub(r"\s+", " ", summary).strip()
            if len(summary) > 500:
                summary = summary[:500] + "..."

            articles.append(Article(
                title=entry.get("title", ""),
                url=article_url,
                summary=summary,
                source="reddit_rss",
                score=0,
                fetched_at=datetime.now(timezone.utc).isoformat(),
            ))

    except Exception as e:
        logger.error(f"Reddit RSS collector error ({feed_url}): {e}")

    return articles


def fetch() -> List[Article]:
    articles: List[Article] = []

    for feed_url in RSS_FEEDS:
        results = _fetch_feed(feed_url, "rss", RSS_FETCH_LIMIT)
        articles.extend(results)
        if results:
            logger.info(f"RSS ({feed_url}): {len(results)} articles")

    for feed_url in REDDIT_RSS_FEEDS:
        results = _fetch_reddit_rss(feed_url, REDDIT_RSS_FETCH_LIMIT)
        articles.extend(results)
        if results:
            logger.info(f"Reddit RSS ({feed_url}): {len(results)} articles")

    logger.info(f"RSS total: {len(articles)} articles")
    return articles
