import logging
import trafilatura

logger = logging.getLogger(__name__)


def fetch_article(url: str) -> str:
    """
    用 trafilatura 抓取文章主體文字。
    失敗時回傳空字串，不拋例外。
    """
    try:
        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            logger.warning(f"fetch_article: no content downloaded from {url}")
            return ""

        text = trafilatura.extract(
            downloaded,
            include_comments=False,
            include_tables=False,
            no_fallback=False,
        )
        if not text:
            logger.warning(f"fetch_article: trafilatura extracted nothing from {url}")
            return ""

        # 限制長度避免超過 context window
        return text[:8000]

    except Exception as e:
        logger.warning(f"fetch_article error ({url}): {e}")
        return ""
