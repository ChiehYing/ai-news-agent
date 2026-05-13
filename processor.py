import html
import json
import logging
import re
import requests
from datetime import datetime, timezone
from typing import List

from config import (
    OPENROUTER_API_KEY,
    OPENROUTER_BASE_URL,
    PROCESSOR_MODEL,
    FILTER_TOP_N,
    AGENT_MAX_TOOL_CALLS,
    FILTER_SYSTEM_PROMPT,
    SUMMARIZE_SYSTEM_PROMPT,
)
from models import Article, ProcessedReport
from tools import fetch_article, web_search

logger = logging.getLogger(__name__)


_TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "fetch_article",
            "description": (
                "Fetch the full text of an article by URL using a content extractor. "
                "Use this when an article's content is empty, too short, or low quality."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "The article URL to fetch."}
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": (
                "Search the web for supplementary information about a topic. "
                "Use this to find background context, related discussions, or details "
                "not covered in the article itself."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query."}
                },
                "required": ["query"],
            },
        },
    },
]

_TOOL_DISPATCH = {
    "fetch_article": lambda args: fetch_article(args["url"]),
    "web_search": lambda args: web_search(args["query"]),
}


def _llm_call(system_prompt: str, user_message: str) -> str:
    """向 OpenRouter 發送一次 LLM 請求（不含 tools），回傳 assistant message 文字。"""
    resp = requests.post(
        f"{OPENROUTER_BASE_URL}/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": PROCESSOR_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
        },
        timeout=180,
    )
    resp.raise_for_status()
    data = resp.json()
    if "choices" not in data:
        logger.error(f"Unexpected API response: {data}")
        raise ValueError(f"API response missing 'choices': {data}")
    return data["choices"][0]["message"]["content"]


def _llm_call_with_tools(system_prompt: str, user_message: str) -> str:
    """
    向 OpenRouter 發送帶工具的 LLM 請求，執行 tool use loop。
    LLM 可以呼叫工具補充資訊，直到輸出最終結果。
    最多執行 AGENT_MAX_TOOL_CALLS 次工具呼叫後強制結束。
    回傳最終的 assistant 文字內容。
    """
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]
    tool_calls_used = 0

    while tool_calls_used < AGENT_MAX_TOOL_CALLS:
        resp = requests.post(
            f"{OPENROUTER_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": PROCESSOR_MODEL,
                "messages": messages,
                "tools": _TOOL_DEFINITIONS,
                "tool_choice": "auto",
            },
            timeout=180,
        )
        resp.raise_for_status()
        data = resp.json()

        if "choices" not in data:
            logger.error(f"Unexpected API response: {data}")
            raise ValueError(f"API response missing 'choices': {data}")

        choice = data["choices"][0]
        message = choice["message"]
        finish_reason = choice.get("finish_reason", "")

        # 把 assistant 訊息加入對話歷史
        messages.append(message)

        if finish_reason != "tool_calls":
            # LLM 決定不再呼叫工具，回傳最終結果
            return message.get("content") or ""

        # 執行所有工具呼叫
        tool_calls = message.get("tool_calls", [])
        if not tool_calls:
            return message.get("content") or ""

        for tc in tool_calls:
            tool_name = tc["function"]["name"]
            try:
                args = json.loads(tc["function"]["arguments"])
            except json.JSONDecodeError:
                args = {}

            if tool_name in _TOOL_DISPATCH:
                logger.info(f"Agent tool call: {tool_name}({args})")
                result = _TOOL_DISPATCH[tool_name](args)
                tool_calls_used += 1
            else:
                logger.warning(f"Unknown tool called: {tool_name}")
                result = f"Error: unknown tool '{tool_name}'"

            messages.append({
                "role": "tool",
                "tool_call_id": tc["id"],
                "content": result or "(no result)",
            })

        logger.info(f"Agent tool calls used so far: {tool_calls_used}/{AGENT_MAX_TOOL_CALLS}")

    # 超過上限，用 tool_choice=none 強制拿最終答案
    logger.warning(f"Agent reached max tool calls ({AGENT_MAX_TOOL_CALLS}), forcing final response")
    resp = requests.post(
        f"{OPENROUTER_BASE_URL}/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": PROCESSOR_MODEL,
            "messages": messages,
            "tools": _TOOL_DEFINITIONS,
            "tool_choice": "none",
        },
        timeout=180,
    )
    resp.raise_for_status()
    data = resp.json()
    if "choices" not in data:
        raise ValueError(f"API response missing 'choices': {data}")
    return data["choices"][0]["message"].get("content") or ""


def _stage1_filter(articles: List[Article]) -> List[str]:
    """
    Stage 1：輸入所有文章的 title + summary，
    回傳 LLM 選出的 TOP N 篇 URL list。
    """
    article_list = "\n\n".join(
        f"[{i+1}] {a.title}\nURL: {a.url}\nSummary: {(a.summary or '')[:150] or '(no summary)'}"
        for i, a in enumerate(articles)
    )
    user_message = f"Here are today's articles:\n\n{article_list}"

    raw = _llm_call(FILTER_SYSTEM_PROMPT, user_message)

    # 解析 JSON array
    # 有些模型會包在 markdown code block 裡，先嘗試擷取
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.splitlines()
        raw = "\n".join(lines[1:-1])

    selected = json.loads(raw)
    urls = [item["url"] for item in selected]
    logger.info(f"Stage 1: selected {len(urls)} articles from {len(articles)}")
    return urls


def _fetch_full_content(article: Article) -> str:
    """
    抓取文章完整內容（純文字）。
    失敗時回傳空字串，不中斷流程。
    """
    try:
        resp = requests.get(article.url, timeout=15, headers={"User-Agent": "ai-news-agent/1.0"})
        resp.raise_for_status()

        content_type = resp.headers.get("Content-Type", "")
        if "text/html" not in content_type and "text/plain" not in content_type:
            return ""

        # 簡單擷取 <body> 內文字，移除 HTML tag
        import re, html
        text = html.unescape(resp.text)
        text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<[^>]+>", "", text)
        text = re.sub(r"\s+", " ", text).strip()

        # 限制長度，避免超過 context window
        return text[:8000]

    except Exception as e:
        logger.warning(f"Failed to fetch full content for {article.url}: {e}")
        return ""


def _stage2_summarize(articles: List[Article]) -> tuple[List[Article], str]:
    """
    Stage 2：批次 LLM call，輸入完整內容，
    回傳填好 ai_summary / tags / learning_note 的 articles，以及 highlights。
    """
    article_blocks = "\n\n---\n\n".join(
        f"URL: {a.url}\nTitle: {a.title}\n\nContent:\n{a.full_content or a.summary or '(no content)'}"
        for a in articles
    )
    user_message = f"Please process the following {len(articles)} articles:\n\n{article_blocks}"

    raw = _llm_call_with_tools(SUMMARIZE_SYSTEM_PROMPT, user_message)

    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.splitlines()
        raw = "\n".join(lines[1:-1])

    try:
        result = json.loads(raw)
    except json.JSONDecodeError as e:
        logger.error(f"Stage 2 JSON parse failed: {e}")
        logger.error(f"Raw response (first 2000 chars):\n{raw[:2000]}")
        raise

    def _clean(text: str) -> str:
        """移除 LLM 輸出中可能夾帶的 HTML 標籤與實體。"""
        text = re.sub(r"<[^>]+>", "", text)
        return html.unescape(text).strip()

    # 將 LLM 輸出回填到 Article 物件（用 URL 對應）
    url_to_article = {a.url: a for a in articles}
    for item in result.get("articles", []):
        article = url_to_article.get(item["url"])
        if not article:
            continue
        article.tags = item.get("tags", [])
        summary = _clean(item.get("summary", ""))
        key_insight = _clean(item.get("key_insight", ""))
        article.ai_summary = summary + (f"\n\n**Key Insight:** {key_insight}" if key_insight else "")
        article.learning_note = _clean(item.get("learning_note", ""))

    highlights = _clean(result.get("highlights", ""))
    logger.info(f"Stage 2: processed {len(articles)} articles")
    return articles, highlights


def process(articles: List[Article]) -> ProcessedReport:
    """
    兩階段 LLM pipeline 的入口。
    輸入所有 collector 合併後的 List[Article]，
    回傳 ProcessedReport。
    """
    if not articles:
        logger.warning("processor received empty article list")
        return ProcessedReport(
            date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            articles=[],
            highlights="",
            generated_at=datetime.now(timezone.utc).isoformat(),
        )

    # Stage 1
    selected_urls = _stage1_filter(articles)
    selected = [a for a in articles if a.url in selected_urls]

    # 若 LLM 回傳 URL 對不上（模型有時會改寫 URL），fallback 取前 N 篇
    if not selected:
        logger.warning("Stage 1 URL match failed, falling back to first N articles")
        selected = articles[:FILTER_TOP_N]

    # 抓完整內容
    for article in selected:
        article.full_content = _fetch_full_content(article)

    # Stage 2
    processed_articles, highlights = _stage2_summarize(selected)

    return ProcessedReport(
        date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        articles=processed_articles,
        highlights=highlights,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )
