import logging
import requests
from datetime import datetime, timezone
from typing import List

from config import REDDIT_SUBREDDITS, REDDIT_TIME_FILTER, REDDIT_FETCH_LIMIT
from models import Article

logger = logging.getLogger(__name__)

REDDIT_JSON_URL = "https://www.reddit.com/r/{subreddit}/top.json"
HEADERS = {"User-Agent": "ai-news-agent/1.0"}


def fetch() -> List[Article]:
    articles: List[Article] = []

    for subreddit in REDDIT_SUBREDDITS:
        try:
            resp = requests.get(
                REDDIT_JSON_URL.format(subreddit=subreddit),
                params={"t": REDDIT_TIME_FILTER, "limit": REDDIT_FETCH_LIMIT},
                headers=HEADERS,
                timeout=10,
            )
            resp.raise_for_status()
            posts = resp.json()["data"]["children"]

            for post in posts:
                data = post["data"]

                # 跳過不含外部連結的純文字貼文（selftext 貼文 url 指向自己）
                url = data.get("url", "")
                if not url or url.startswith("https://www.reddit.com"):
                    continue

                summary = data.get("selftext", "").strip()
                if len(summary) > 500:
                    summary = summary[:500] + "..."

                articles.append(Article(
                    title=data["title"],
                    url=url,
                    summary=summary,
                    source="reddit",
                    score=data.get("score", 0),
                    fetched_at=datetime.now(timezone.utc).isoformat(),
                ))

        except Exception as e:
            logger.error(f"Reddit collector error (r/{subreddit}): {e}")

    logger.info(f"Reddit: fetched {len(articles)} articles")
    return articles
