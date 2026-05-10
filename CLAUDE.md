# AI News Agent — 專案規格書

## 這個系統在做什麼

每天自動從 Reddit、Hacker News、AI 公司部落格抓取高品質 AI 文章，
用 LLM 篩選出最值得學習的文章（數量由 config.py 的 FILTER_TOP_N 控制）
並整理成繁體中文摘要，透過 Email 推送給使用者，
同時存成 Markdown 檔案備存於 GitHub。

## 架構圖

來源設定（config.py）
    ↓ subreddit 清單、RSS URL 清單
collectors/（各來源獨立檔案）
    ↓ List[Article]
processor.py（兩階段 LLM Pipeline）
    ↓ ProcessedReport
output/
    ├── markdown.py → /reports/YYYY-MM-DD.md
    └── email_sender.py → Gmail SMTP

## Module Responsibilities

### collectors/
- One file per source, returns List[Article] only
- NEVER call LLM
- NEVER write to files
- NEVER filter or evaluate article quality
- NEVER return any format other than List[Article]
- On any error: log the error and return []

### processor.py
Two-stage fixed pipeline (NOT an Agent):

Stage 1 — Coarse filter:
- Input: List[Article] with title + summary only
- Task: select top N most valuable articles
        (N is controlled by FILTER_TOP_N in config.py)
- One LLM call total

Stage 2 — Deep processing:
- Fetch full content for selected 10 articles only
- Input: full content + reader profile
- Task: summarize, tag, add learning notes
- One batched LLM call (NOT one call per article)
- Returns: ProcessedReport

### output/
- Accept ProcessedReport only
- NEVER call LLM
- NEVER modify report content
- markdown.py: save to /reports/YYYY-MM-DD.md
- email_sender.py: send via Gmail SMTP

### main.py
固定執行順序，不包含任何商業邏輯：
1. 執行所有 collector，合併結果
2. 比對 seen_urls.json，過濾已處理文章
3. 執行 processor
4. 執行所有 output
5. 更新 seen_urls.json
6. Commit 變更回 GitHub

- NEVER contains business logic
- NEVER calls LLM directly

## Data Contracts

```python
@dataclass
class Article:
    title: str
    url: str
    summary: str        # 平台提供的摘要，可能為空
    source: str         # "reddit" | "hackernews" | "rss"
    score: int          # 投票數或排名
    fetched_at: str     # ISO 8601
    full_content: str = ""
    tags: list[str] = field(default_factory=list)
    ai_summary: str = ""
    learning_note: str = ""

@dataclass
class ProcessedReport:
    date: str
    articles: List[Article]
    highlights: str
    generated_at: str
```

## Configuration Rules

- ALL environment-dependent values in config.py only
- NO hardcoded URLs, model names, or paths anywhere else
- Switch models by changing config.py only

## Environment Variables

本機：.env 檔案
GitHub Actions：GitHub Secrets