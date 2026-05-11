# AI News Agent

每天自動從 Reddit、Hacker News、AI 公司部落格抓取高品質 AI 文章，
用 LLM 篩選出最值得學習的文章，整理成繁體中文摘要，
透過 Email 推送，同時存成 Markdown 備存於 GitHub。

## 功能

- 每日 07:00（台灣時間）自動執行
- 多來源抓取：HackerNews、Reddit RSS、AI 公司部落格、技術社群
- 兩階段 LLM Pipeline：先篩選，再深度摘要
- 輸出繁體中文摘要、標籤、學習筆記
- Email 推送 + Markdown 報告（相容 Obsidian Git 同步）

## 架構

```
config.py（來源設定、LLM 設定、Prompt）
    ↓
collectors/          各來源獨立抓取，回傳 List[Article]
  ├── reddit.py      Reddit JSON API（需 OAuth，目前備用）
  ├── hackernews.py  HN Firebase API
  └── rss.py         RSS + Reddit RSS
    ↓
processor.py         兩階段 LLM Pipeline
  Stage 1：title + summary → 篩選 TOP N 篇
  Stage 2：完整內容 → 批次摘要、標籤、學習筆記
    ↓
output/
  ├── markdown.py    → reports/YYYY-MM-DD.md
  └── email_sender.py → Gmail SMTP
    ↓
main.py              更新 seen_urls.json + git commit/push
```

## 來源

| 來源 | 說明 |
|---|---|
| Hacker News | Top stories，Firebase API |
| Reddit RSS | r/LocalLLaMA、r/MachineLearning、r/ChatGPT、r/ClaudeAI、r/PromptEngineering、r/AIAssistants、r/vibecoding |
| Anthropic Blog | 社群維護 RSS feed |
| OpenAI Blog | 官方 RSS |
| DeepMind Blog | 官方 RSS |
| Simon Willison | 個人部落格，AI 實戰分析 |
| HuggingFace Blog | 模型與工具發布 |
| Latent Space | AI Engineer newsletter |
| DEV.to | ai、llm 標籤文章 |

## 設定

### 環境變數

複製 `.env.example` 為 `.env` 並填入：

```
OPENROUTER_API_KEY=    # OpenRouter API key
PROCESSOR_MODEL=       # 可選，覆蓋預設模型
GMAIL_ADDRESS=         # Gmail 帳號
GMAIL_APP_PASSWORD=    # Gmail 應用程式密碼（非登入密碼）
EMAIL_RECIPIENTS=      # 收件人，逗號分隔
```

### 主要設定（config.py）

```python
FILTER_TOP_N = 10           # 每日精選篇數
FILTER_MAX_PER_SOURCE = 2   # 每個來源最多幾篇（None 不限制，或用 (1,3) 設範圍）
PROCESSOR_MODEL = "nvidia/nemotron-3-nano-30b-a3b:free"  # OpenRouter 模型
```

## 安裝與執行

```bash
pip install -r requirements.txt
cp .env.example .env
# 填入 .env 後執行
python main.py
```

## GitHub Actions 自動化

1. Fork 或 clone 此 repo
2. 在 repo Settings → Secrets 新增：
   - `OPENROUTER_API_KEY`
   - `PROCESSOR_MODEL`（可選）
   - `GMAIL_ADDRESS`
   - `GMAIL_APP_PASSWORD`
   - `EMAIL_RECIPIENTS`
3. Actions 每天 UTC 23:00（台灣時間 07:00）自動執行
4. 也可在 Actions 頁面手動觸發

## 報告格式

每日報告存於 `reports/YYYY-MM-DD.md`，包含：

- 今日精選綜合說明
- 每篇文章：繁體中文標題、來源、標籤、摘要、Key Insight、學習筆記

## 技術

- Python 3.11+
- LLM：[OpenRouter](https://openrouter.ai)（OpenAI-compatible API）
- Email：Gmail SMTP
- 自動化：GitHub Actions
