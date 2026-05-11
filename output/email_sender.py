import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from config import GMAIL_ADDRESS, GMAIL_APP_PASSWORD, EMAIL_RECIPIENTS
from models import ProcessedReport
from output import source_label

logger = logging.getLogger(__name__)


def _build_html(report: ProcessedReport) -> str:
    """將 ProcessedReport 轉成 HTML Email 內容。"""
    parts = []
    parts.append(f"<h1>AI 新聞摘要 {report.date}</h1>")
    parts.append(f"<p><em>產生時間：{report.generated_at}</em></p>")
    parts.append("<hr>")
    parts.append("<h2>今日精選</h2>")
    parts.append(f"<p>{report.highlights}</p>")
    parts.append("<hr>")

    for i, article in enumerate(report.articles, 1):
        tags_html = " ".join(
            f'<code style="background:#f0f0f0;padding:2px 6px;border-radius:3px">{t}</code>'
            for t in article.tags
        ) if article.tags else ""

        parts.append(f'<h2>{i}. <a href="{article.url}">{article.title}</a></h2>')
        if tags_html:
            parts.append(f"<p>{tags_html}</p>")
        label = source_label(article)
        score_str = f" | <strong>評分：</strong>{article.score}" if article.score else ""
        parts.append(f"<p><strong>來源：</strong>{label}{score_str}</p>")
        parts.append("<h3>摘要</h3>")
        parts.append(f"<p>{article.ai_summary.replace(chr(10), '<br>')}</p>")
        parts.append("<h3>學習筆記</h3>")
        parts.append(f"<p>{article.learning_note.replace(chr(10), '<br>')}</p>")
        parts.append("<hr>")

    return "\n".join(parts)


def send(report: ProcessedReport) -> None:
    """透過 Gmail SMTP 發送每日摘要 Email。"""
    recipients = [r.strip() for r in EMAIL_RECIPIENTS.split(",") if r.strip()]
    if not recipients:
        logger.error("EMAIL_RECIPIENTS is empty, skipping email")
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"[AI News] {report.date} 每日摘要（{len(report.articles)} 篇）"
    msg["From"] = GMAIL_ADDRESS
    msg["To"] = ", ".join(recipients)

    html_content = _build_html(report)
    msg.attach(MIMEText(html_content, "html", "utf-8"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_ADDRESS, recipients, msg.as_string())
        logger.info(f"Email sent to: {', '.join(recipients)}")
    except Exception as e:
        logger.error(f"Email send failed: {e}")
        raise
