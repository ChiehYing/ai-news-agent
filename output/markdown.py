import logging
import os
from models import ProcessedReport
from config import REPORTS_DIR
from output import source_label

logger = logging.getLogger(__name__)


def save(report: ProcessedReport) -> str:
    """
    將 ProcessedReport 存成 Markdown 檔案。
    回傳儲存路徑。
    """
    os.makedirs(REPORTS_DIR, exist_ok=True)
    filepath = os.path.join(REPORTS_DIR, f"{report.date}.md")

    lines = []
    lines.append(f"# AI 新聞摘要 {report.date}")
    lines.append("")
    lines.append(f"> 產生時間：{report.generated_at}")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 今日精選")
    lines.append("")
    lines.append(report.highlights)
    lines.append("")
    lines.append("---")
    lines.append("")

    for i, article in enumerate(report.articles, 1):
        tags_str = " ".join(f"`{t}`" for t in article.tags) if article.tags else ""
        lines.append(f"## {i}. {article.title}")
        lines.append("")
        if tags_str:
            lines.append(tags_str)
            lines.append("")
        label = source_label(article)
        score_str = f" | **評分：** {article.score}" if article.score else ""
        lines.append(f"**來源：** {label}{score_str} | [原文連結]({article.url})")
        lines.append("")
        lines.append("### 摘要")
        lines.append("")
        lines.append(article.ai_summary)
        lines.append("")
        lines.append("### 學習筆記")
        lines.append("")
        lines.append(article.learning_note)
        lines.append("")
        lines.append("---")
        lines.append("")

    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    logger.info(f"Markdown saved: {filepath}")
    return filepath
