import html as html_lib
import re
import requests
import trafilatura
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) "
        "Version/18.0 Safari/605.1.15"
    ),
    "Accept-Language": "fi-FI,fi;q=0.9,en;q=0.8",
}

def clean_fragment(value):
    if not value:
        return ""
    soup = BeautifulSoup(value, "html.parser")
    return html_lib.unescape(" ".join(soup.stripped_strings))

def normalize(value):
    value = html_lib.unescape(value or "")
    value = re.sub(r"[ \t]+", " ", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    return value.strip()

def fetch_article(url, fallback_description=""):
    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()

    raw = response.text
    text = trafilatura.extract(
        raw,
        include_comments=False,
        include_tables=False,
        include_links=False,
        favor_precision=True,
    ) or ""

    soup = BeautifulSoup(raw, "html.parser")

    title = ""
    meta = soup.find("meta", attrs={"property": "og:title"})
    if meta and meta.get("content"):
        title = meta["content"].strip()
    if not title and soup.title:
        title = soup.title.get_text(" ", strip=True)

    image_url = ""
    image_meta = (
        soup.find("meta", attrs={"property": "og:image"})
        or soup.find("meta", attrs={"name": "twitter:image"})
        or soup.find("meta", attrs={"property": "twitter:image"})
    )
    if image_meta and image_meta.get("content"):
        image_url = image_meta["content"].strip()

    description = ""
    meta = soup.find("meta", attrs={"property": "og:description"})
    if meta and meta.get("content"):
        description = meta["content"].strip()
    if not description:
        description = clean_fragment(fallback_description)

    text = normalize(text)
    title = normalize(title)
    description = normalize(description)

    if len(text) < 200 and description:
        text = description

    return {
        "title": title,
        "description": description,
        "text": text,
        "image_url": image_url,
        "url": url,
    }
