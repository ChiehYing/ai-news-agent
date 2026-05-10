import os
from dotenv import load_dotenv

load_dotenv()

# === API Keys ===
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")

# === Email 設定 ===
GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS", "")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")
EMAIL_RECIPIENTS = os.getenv("EMAIL_RECIPIENTS", "")

# === 模型設定 ===
PROCESSOR_MODEL = os.getenv(
    "PROCESSOR_MODEL",
    "nvidia/nemotron-3-nano-30b-a3b:free"    # 開發階段預設，之後換
)
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# === 來源設定 ===
REDDIT_SUBREDDITS = ["LocalLLaMA", "MachineLearning", "ChatGPT"]
REDDIT_TIME_FILTER = "week"     # top/week 高票文章

RSS_FEEDS = [
    "https://www.anthropic.com/rss.xml",
    "https://openai.com/blog/rss.xml",
    "https://deepmind.google/blog/rss.xml",
]

# === 數量控制 ===
REDDIT_FETCH_LIMIT = 20     # 每個 subreddit 抓幾篇
HN_FETCH_LIMIT = 30         # HN 抓幾篇
RSS_FETCH_LIMIT = 10        # 每個 RSS 來源抓幾篇
FILTER_TOP_N = 10           # 第一階段篩選後保留幾篇送入摘要

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

### Content I Want（優先順序）
1. Practical experience sharing: what someone built and what they learned
2. Model usage tips: prompt techniques, quirks, comparisons
3. New AI tools: hands-on evaluation, real usage experience
   (e.g. OpenClaw, Cursor, vibe coding tools, memory management)
4. Agent and RAG implementation insights
5. Workflow and productivity tips from AI practitioners
6. Significant model releases that affect developers

### Content to Exclude
- Academic papers without practical application
- Pure business news and fundraising announcements
- Beginner tutorials covering basics already mastered
- Marketing content without substance
"""

# === Processor System Prompts ===
FILTER_SYSTEM_PROMPT = f"""
You are an expert AI content curator.

{READER_PROFILE}

## Your Task
Given a list of articles with titles and summaries, select the TOP {FILTER_TOP_N}
most valuable articles for this reader.

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

## Output Format
Return a JSON object only. No markdown, no explanation, no other text.

{{
  "articles": [
    {{
      "url": "article url",
      "title": "繁體中文標題",
      "tags": ["RAG", "Agent"],
      "summary": "核心內容摘要，3-5句話，聚焦在對開發者最有價值的部分",
      "key_insight": "這篇文章最重要的一個洞察或技巧",
      "learning_note": "結合讀者目前的學習階段，這篇內容可以怎麼應用"
    }}
  ],
  "highlights": "今日精選前三名的綜合說明，繁體中文段落，說明為什麼這三篇特別值得優先閱讀"
}}
"""