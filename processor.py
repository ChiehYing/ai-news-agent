import json
import logging
import requests
from datetime import datetime, timezone
from typing import List

from config import (
    OPENROUTER_API_KEY,
    OPENROUTER_BASE_URL,
    PROCESSOR_MODEL,
    FILTER_TOP_N,
    FILTER_SYSTEM_PROMPT,
    SUMMARIZE_SYSTEM_PROMPT,
)
from models import Article, ProcessedReport

logger = logging.getLogger(__name__)


def _llm_call(system_prompt: str, user_message: str) -> str:
    """向 OpenRouter 發送一次 LLM 請求，回傳 assistant message 文字。"""
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


def _stage1_filter(articles: List[Article]) -> List[str]:
    """
    Stage 1：輸入所有文章的 title + summary，
    回傳 LLM 選出的 TOP N 篇 URL list。
    """
    article_list = "\n\n".join(
        f"[{i+1}] {a.title}\nURL: {a.url}\nSummary: {(a.summary or '')[:150] or '(no summary)'}"
        for i, a in enumerate(articles)
    )
    user_message = f"以下是今日收集的文章，請依照讀者 profile 選出最有價值的 {FILTER_TOP_N} 篇：\n\n{article_list}"

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
    user_message = f"請處理以下 {len(articles)} 篇文章：\n\n{article_blocks}"

    raw = _llm_call(SUMMARIZE_SYSTEM_PROMPT, user_message)

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

    # 將 LLM 輸出回填到 Article 物件（用 URL 對應）
    url_to_article = {a.url: a for a in articles}
    for item in result.get("articles", []):
        article = url_to_article.get(item["url"])
        if not article:
            continue
        article.tags = item.get("tags", [])
        article.ai_summary = item.get("summary", "") + (
            f"\n\n**Key Insight:** {item['key_insight']}" if item.get("key_insight") else ""
        )
        article.learning_note = item.get("learning_note", "")

    highlights = result.get("highlights", "")
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
