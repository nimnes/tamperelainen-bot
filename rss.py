from dataclasses import dataclass
import feedparser
import requests
from config import RSS_URL, RSS_LIMIT

@dataclass
class Article:
    title: str
    url: str
    description: str
    published: str
    category: str

HEADERS = {"User-Agent": "TamperelainenEnglishNewsBot/1.0"}

def fetch_articles():
    r = requests.get(RSS_URL, headers=HEADERS, timeout=30)
    r.raise_for_status()
    feed = feedparser.parse(r.content)

    if feed.bozo and not feed.entries:
        raise RuntimeError(f"RSS parse error: {feed.bozo_exception}")

    result = []
    for entry in feed.entries[:RSS_LIMIT]:
        url = entry.get("link", "").strip()
        title = entry.get("title", "").strip()
        if not url or not title:
            continue

        result.append(Article(
            title=title,
            url=url,
            description=entry.get("description", "") or entry.get("summary", ""),
            published=entry.get("published", "") or entry.get("updated", ""),
            category=entry.get("category", "") or "News"
        ))

    return result
