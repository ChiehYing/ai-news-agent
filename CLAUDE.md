# AI News Agent — 專案規格書

## 這個系統在做什麼

每天自動從 Reddit、Hacker News、AI 公司部落格抓取高品質 AI 文章，
用 LLM 篩選出最值得學習的文章（數量由 config.py 的 FILTER_TOP_N 控制），
整理成繁體中文摘要，透過 Email 推送給使用者，
同時存成 Markdown 檔案備存於 GitHub。

## 架構圖

來源設定（config.py）
    ↓ subreddit 清單、RSS URL 清單
collectors/（各來源獨立檔案）
    ↓ List[Article]
processor.py（兩階段 Pipeline，Stage 2 為 Agent）
    ↓ ProcessedReport
tools/（Stage 2 Agent 可用工具）
    ├── fetch.py → fetch_article
    └── search.py → web_search
output/
    ├── markdown.py → /reports/YYYY-MM-DD.md
    └── email_sender.py → Gmail SMTP

## 模組職責

### collectors/
- 每個來源一個檔案，只回傳 List[Article]
- 禁止呼叫 LLM
- 禁止寫入檔案
- 禁止篩選或評估文章品質
- 禁止回傳 List[Article] 以外的格式
- 發生任何錯誤：記錄 log 並回傳 []

### processor.py
兩階段 Pipeline，Stage 2 為 Agent：

Stage 1 — 粗篩：
- 輸入：List[Article]，只含 title + summary
- 任務：選出最有價值的前 N 篇（N 由 config.py 的 FILTER_TOP_N 控制）
- 固定一次 LLM call

Stage 2 — 深度處理（Agent loop）：
- 只對選出的文章抓取完整內容
- 輸入：完整內容 + reader profile
- LLM 可自主呼叫工具補充資訊（fetch_article、web_search）
- 任務：批次摘要、標籤、學習筆記（不是每篇一次 call）
- 回傳：ProcessedReport

### tools/
- 只供 Stage 2 Agent 使用
- 禁止呼叫 LLM
- 禁止寫入檔案
- fetch_article(url)：用 trafilatura 抓取文章全文；失敗回傳空字串
- web_search(query)：網路搜尋，DuckDuckGo → Tavily 兩層備援；失敗回傳空字串

### output/
- 只接受 ProcessedReport
- 禁止呼叫 LLM
- 禁止修改 report 內容
- markdown.py：存至 /reports/YYYY-MM-DD.md
- email_sender.py：透過 Gmail SMTP 發送

### main.py
固定執行順序，不包含任何商業邏輯：
1. 執行所有 collector，合併結果
2. 比對 seen_urls.json，過濾已處理文章
3. 執行 processor
4. 執行所有 output
5. 更新 seen_urls.json
6. Commit 變更回 GitHub

- 禁止包含商業邏輯
- 禁止直接呼叫 LLM

## 資料合約

```python
@dataclass
class Article:
    title: str
    url: str
    summary: str        # 平台提供的摘要，可能為空
    source: str         # "reddit" | "hackernews" | "rss" | "reddit_rss"
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

## 設定規則

- 所有環境相關的值只能放在 config.py
- 禁止在其他地方 hardcode URL、模型名稱或路徑
- 換模型只改 config.py

## 環境變數

本機：.env 檔案
GitHub Actions：GitHub Secrets
