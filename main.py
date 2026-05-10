import json
import logging
import subprocess
import sys
from datetime import datetime, timezone

from config import SEEN_URLS_FILE, REPORTS_DIR
from collectors import reddit, hackernews, rss
from processor import process
from output import markdown, email_sender

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def load_seen_urls() -> set[str]:
    try:
        with open(SEEN_URLS_FILE, encoding="utf-8") as f:
            return set(json.load(f))
    except FileNotFoundError:
        return set()


def save_seen_urls(seen: set[str]) -> None:
    with open(SEEN_URLS_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(seen), f, indent=2)


def git_commit(date: str) -> None:
    try:
        subprocess.run(["git", "add", REPORTS_DIR, SEEN_URLS_FILE], check=True)
        subprocess.run(
            ["git", "commit", "-m", f"report: {date}"],
            check=True,
        )
        subprocess.run(["git", "push"], check=True)
        logger.info("Git commit and push done")
    except subprocess.CalledProcessError as e:
        logger.error(f"Git operation failed: {e}")


def main() -> None:
    logger.info("=== AI News Agent start ===")

    # 1. 執行所有 collector，合併結果
    articles = []
    articles.extend(reddit.fetch())
    articles.extend(hackernews.fetch())
    articles.extend(rss.fetch())
    logger.info(f"Total collected: {len(articles)} articles")

    # 2. 過濾已處理文章
    seen_urls = load_seen_urls()
    new_articles = [a for a in articles if a.url not in seen_urls]
    logger.info(f"New articles (not seen before): {len(new_articles)}")

    if not new_articles:
        logger.info("No new articles, exiting")
        sys.exit(0)

    # 3. 執行 processor
    report = process(new_articles)

    # 4. 執行所有 output
    markdown.save(report)
    email_sender.send(report)

    # 5. 更新 seen_urls.json
    new_urls = {a.url for a in articles}
    seen_urls.update(new_urls)
    save_seen_urls(seen_urls)
    logger.info(f"seen_urls.json updated ({len(seen_urls)} total)")

    # 6. Commit 回 GitHub
    git_commit(report.date)

    logger.info("=== AI News Agent done ===")


if __name__ == "__main__":
    main()
