from urllib.parse import urlparse
from models import Article

_DOMAIN_LABELS = {
    "openai.com": "OpenAI Blog",
    "deepmind.google": "DeepMind Blog",
    "anthropic.com": "Anthropic Blog",
    "simonwillison.net": "Simon Willison",
    "huggingface.co": "HuggingFace Blog",
    "latent.space": "Latent Space",
    "dev.to": "DEV.to",
}


def source_label(article: Article) -> str:
    """回傳人類可讀的來源標籤。"""
    if article.source == "hackernews":
        return "Hacker News"

    if article.source == "reddit":
        return "Reddit"

    if article.source == "reddit_rss":
        parts = urlparse(article.url).path.strip("/").split("/")
        try:
            r_idx = parts.index("r")
            return f"r/{parts[r_idx + 1]}"
        except (ValueError, IndexError):
            return "Reddit"

    # source == "rss"：從 domain 對應友善名稱
    domain = urlparse(article.url).netloc.replace("www.", "")
    return _DOMAIN_LABELS.get(domain, domain)
