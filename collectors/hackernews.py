import logging
import requests
from datetime import datetime, timezone
from typing import List

from config import HN_FETCH_LIMIT
from models import Article

logger = logging.getLogger(__name__)

HN_TOP_URL = "https://hacker-news.firebaseio.com/v0/topstories.json"
HN_ITEM_URL = "https://hacker-news.firebaseio.com/v0/item/{id}.json"


def _strip_html(text: str) -> str:
    """移除 HTML tag 並解碼 HTML 實體，HN 的 text 欄位為 HTML。"""
    import re
    import html
    text = re.sub(r"<[^>]+>", "", text)
    return html.unescape(text).strip()


def fetch() -> List[Article]:
    articles: List[Article] = []

    try:
        resp = requests.get(HN_TOP_URL, timeout=10)
        resp.raise_for_status()
        story_ids = resp.json()[:HN_FETCH_LIMIT]
    except Exception as e:
        logger.error(f"HN collector error (top stories): {e}")
        return []

    for story_id in story_ids:
        try:
            resp = requests.get(HN_ITEM_URL.format(id=story_id), timeout=10)
            resp.raise_for_status()
            item = resp.json()

            # 只處理有外部 URL 的 story（Ask HN / Show HN 純文字貼文略過）
            url = item.get("url", "")
            if not url:
                continue

            raw_text = item.get("text", "") or ""
            summary = _strip_html(raw_text)
            if len(summary) > 500:
                summary = summary[:500] + "..."

            articles.append(Article(
                title=item.get("title", ""),
                url=url,
                summary=summary,
                source="hackernews",
                score=item.get("score", 0),
                fetched_at=datetime.now(timezone.utc).isoformat(),
            ))

        except Exception as e:
            logger.error(f"HN collector error (item {story_id}): {e}")

    logger.info(f"HackerNews: fetched {len(articles)} articles")
    return articles
