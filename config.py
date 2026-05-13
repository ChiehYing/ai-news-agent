import os
from dotenv import load_dotenv

load_dotenv()

# === API Keys ===
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")

# === Email 設定 ===
GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS", "")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")
EMAIL_RECIPIENTS = os.getenv("EMAIL_RECIPIENTS", "")

# === 模型設定 ===
PROCESSOR_MODEL = os.getenv(
    "PROCESSOR_MODEL",
    "nvidia/nemotron-3-nano-30b-a3b:free"
)
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# === 來源設定 ===

# HackerNews API
HN_TOP_URL = "https://hacker-news.firebaseio.com/v0/topstories.json"
HN_ITEM_URL = "https://hacker-news.firebaseio.com/v0/item/{id}.json"

# Reddit OAuth API（申請成功後啟用）
REDDIT_SUBREDDITS = ["LocalLLaMA", "MachineLearning", "ChatGPT", "ClaudeAI", "PromptEngineering", "AIAssistants", "vibecoding"]
REDDIT_TIME_FILTER = "week"

# Reddit RSS（OAuth API 備援，目前主要使用）
REDDIT_RSS_FEEDS = [
    "https://www.reddit.com/r/LocalLLaMA/top/.rss?t=week",
    "https://www.reddit.com/r/MachineLearning/top/.rss?t=week",
    "https://www.reddit.com/r/ChatGPT/top/.rss?t=week",
    "https://www.reddit.com/r/ClaudeAI/top/.rss?t=week",
    "https://www.reddit.com/r/PromptEngineering/top/.rss?t=week",
    "https://www.reddit.com/r/AIAssistants/top/.rss?t=week",
    "https://www.reddit.com/r/vibecoding/top/.rss?t=week",
]

# 一般 RSS（AI 公司官方部落格 + 高品質個人/社群來源）
RSS_FEEDS = [
    "https://raw.githubusercontent.com/taobojlen/anthropic-rss-feed/main/anthropic_news_rss.xml",
    "https://openai.com/blog/rss.xml",
    "https://deepmind.google/blog/rss.xml",
    "https://simonwillison.net/atom/everything/",
    "https://huggingface.co/blog/feed.xml",
    "https://www.latent.space/feed",
    "https://dev.to/feed/tag/ai",
    "https://dev.to/feed/tag/llm",
]

# === 數量控制 ===
REDDIT_FETCH_LIMIT = 20     # 每個 subreddit 抓幾篇（OAuth API 用）
REDDIT_RSS_FETCH_LIMIT = 10 # 每個 Reddit RSS 來源抓幾篇
HN_FETCH_LIMIT = 30         # HN 抓幾篇
RSS_FETCH_LIMIT = 10        # 每個 RSS 來源抓幾篇
FILTER_TOP_N = 10           # 第一階段篩選後保留幾篇送入摘要
AGENT_MAX_TOOL_CALLS = 20   # Stage 2 Agent loop 最多工具呼叫次數

# 每個來源 domain 最多可以被選幾篇
# None  → 不限制
# 3     → 最多 3 篇
# (1,3) → 最少 1 篇、最多 3 篇
FILTER_MAX_PER_SOURCE = 2

# === 路徑設定 ===
REPORTS_DIR = "./reports"
SEEN_URLS_FILE = "./seen_urls.json"

# === Reader Profile（兩個 processor prompt 共用）===
READER_PROFILE = """
## Reader Profile

### Learning Stage
- Completed: Cloud API, local models (Ollama), RAG, basic Agent
- Currently: Building agents from scratch, learning agentic frameworks
- Stack: Python, Ollama (qwen3:14b), ChromaDB, OpenAI-compatible APIs

### Content I Want (Priority Order)
1. Practical experience sharing: what someone built and what they learned
2. Model usage tips: prompt techniques, quirks, comparisons
3. New AI tools: hands-on evaluation, real usage experience
   (e.g. OpenClaw, Cursor, vibe coding tools, memory management)
4. Agent and RAG implementation insights
5. Workflow and productivity tips from AI practitioners
6. Significant model releases that affect developers

### Also Welcome (Even from Non-Top Sources)
- AI usage tips and workflows shared by everyday developers
- Implementation experience including pitfalls and how they were solved
- Personal experiment results on prompt techniques
These are as valuable for learners as articles from professional sources.

### Content to Exclude
- Academic papers without practical application
- Pure business news and fundraising announcements
- Beginner tutorials covering basics already mastered
- Marketing content without substance
"""

def _source_limit_rule(limit) -> str:
    if limit is None:
        return ""
    if isinstance(limit, int):
        return f"\n- No more than {limit} articles from the same source domain."
    min_n, max_n = limit
    return f"\n- Select between {min_n} and {max_n} articles from the same source domain."


# === Processor System Prompts ===
FILTER_SYSTEM_PROMPT = f"""
You are an expert AI content curator.

{READER_PROFILE}

## Your Task
Given a list of articles with titles and summaries, evaluate each one against the reader profile above.

## Selection Rules
- Select the TOP {FILTER_TOP_N} most valuable articles for this reader.{_source_limit_rule(FILTER_MAX_PER_SOURCE)}

## Output Format
Return a JSON array only. No explanation, no markdown, no other text.

[
  {{
    "url": "article url",
    "reason": "為什麼這篇對這個讀者有價值（繁體中文，一句話）",
    "priority": 1
  }}
]
"""

SUMMARIZE_SYSTEM_PROMPT = f"""
You are an AI learning assistant helping a developer digest English
AI articles into Traditional Chinese.

{READER_PROFILE}

## Your Task
Process all provided articles and generate a structured daily digest.

## Tools
You have two tools available. Use them proactively when needed — do not wait until all articles are processed.

- fetch_article(url): Call this when an article's content is missing, too short (under 3 sentences), or clearly boilerplate. Prefer this over summarizing from title alone.
- web_search(query): Call this when an article mentions a specific tool, model, or technique you need more context on to write a useful learning_note.

## Language Rule
ALL text fields (title, summary, key_insight, learning_note, highlights) MUST be written in Traditional Chinese (繁體中文).
Do NOT write any English prose in these fields.
Tags may remain in English as they are technical terms.
Do NOT use any HTML tags (e.g. &lt;br&gt;, &lt;p&gt;, &lt;b&gt;) in any text field. Use plain text only.

## Output Format
Return a JSON object only. No markdown, no explanation, no other text.

{{
  "articles": [
    {{
      "url": "article url",
      "title": "翻譯成繁體中文的標題",
      "tags": ["RAG", "Agent"],
      "summary": "3到5句繁體中文摘要，聚焦對開發者最有價值的部分",
      "key_insight": "這篇文章最重要的一個洞察或技巧（繁體中文）",
      "learning_note": "結合讀者目前學習階段的應用建議（繁體中文）"
    }}
  ],
  "highlights": "今日精選的綜合說明，繁體中文段落"
}}
"""
