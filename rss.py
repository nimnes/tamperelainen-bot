import time
from dataclasses import dataclass

import feedparser
import requests

from config import RSS_URL, RSS_LIMIT

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "application/rss+xml, application/xml, text/xml, */*",
    "Accept-Language": "en-US,en;q=0.9",
}


@dataclass(frozen=True)
class Article:
    title: str
    url: str
    published: str
    description: str


def fetch_articles():
    last_error = None

    # One retry is enough for the occasional transient RSS failure.
    for attempt in range(2):
        try:
            response = requests.get(RSS_URL, headers=HEADERS, timeout=30)

            if response.status_code == 403 and attempt == 0:
                print("RSS returned HTTP 403. Retrying once in 10 seconds...")
                time.sleep(10)
                continue

            response.raise_for_status()

            feed = feedparser.parse(response.content)
            if feed.bozo and not feed.entries:
                raise RuntimeError(
                    f"RSS feed could not be parsed: {feed.bozo_exception}"
                )

            articles = []
            for entry in feed.entries[:RSS_LIMIT]:
                articles.append(
                    Article(
                        title=entry.get("title", "").strip(),
                        url=entry.get("link", "").strip(),
                        published=entry.get("published", ""),
                        description=entry.get("summary", ""),
                    )
                )

            return articles

        except requests.RequestException as exc:
            last_error = exc
            if attempt == 0:
                print(f"RSS request failed: {exc}. Retrying once in 10 seconds...")
                time.sleep(10)
            else:
                print(f"RSS request failed after retry: {exc}")

        except Exception as exc:
            last_error = exc
            break

    # A temporary RSS failure should not make the scheduled workflow red.
    print(f"WARNING: Could not fetch RSS feed: {last_error}")
    return []
