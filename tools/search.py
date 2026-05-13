import logging
from config import TAVILY_API_KEY

logger = logging.getLogger(__name__)


def web_search(query: str, max_results: int = 3) -> str:
    """
    搜尋網路，回傳結果摘要文字。
    先試 DuckDuckGo，技術性失敗才自動切換 Tavily。
    失敗時回傳空字串，不拋例外。
    """
    result = _search_duckduckgo(query, max_results)
    if result:
        return result

    logger.info(f"web_search: DuckDuckGo failed for '{query}', falling back to Tavily")
    return _search_tavily(query, max_results)


def _search_duckduckgo(query: str, max_results: int) -> str:
    try:
        from ddgs import DDGS
        with DDGS() as ddgs:
            hits = list(ddgs.text(query, max_results=max_results))

        if not hits:
            return ""

        lines = []
        for h in hits:
            title = h.get("title", "")
            body = h.get("body", "")
            href = h.get("href", "")
            lines.append(f"- {title}: {body} ({href})")
        return "\n".join(lines)

    except Exception as e:
        logger.warning(f"DuckDuckGo search error: {e}")
        return ""


def _search_tavily(query: str, max_results: int) -> str:
    if not TAVILY_API_KEY:
        logger.warning("web_search: Tavily fallback skipped, TAVILY_API_KEY not set")
        return ""

    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=TAVILY_API_KEY)
        resp = client.search(query, max_results=max_results)

        hits = resp.get("results", [])
        if not hits:
            return ""

        lines = []
        for h in hits:
            title = h.get("title", "")
            content = h.get("content", "")
            url = h.get("url", "")
            lines.append(f"- {title}: {content} ({url})")
        return "\n".join(lines)

    except Exception as e:
        logger.warning(f"Tavily search error: {e}")
        return ""
