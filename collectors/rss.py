import logging
import feedparser
from datetime import datetime, timezone
from typing import List

from config import RSS_FEEDS, RSS_FETCH_LIMIT
from models import Article

logger = logging.getLogger(__name__)


def fetch() -> List[Article]:
    articles: List[Article] = []

    for feed_url in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)

            if feed.bozo and not feed.entries:
                logger.error(f"RSS collector error ({feed_url}): {feed.bozo_exception}")
                continue

            for entry in feed.entries[:RSS_FETCH_LIMIT]:
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
                    source="rss",
                    score=0,    # RSS 沒有投票數
                    fetched_at=datetime.now(timezone.utc).isoformat(),
                ))

        except Exception as e:
            logger.error(f"RSS collector error ({feed_url}): {e}")

    logger.info(f"RSS: fetched {len(articles)} articles")
    return articles
