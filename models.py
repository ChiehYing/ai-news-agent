from dataclasses import dataclass, field
from typing import List


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
