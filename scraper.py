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

def _srcset_candidates(srcset, base_url):
    """Return (width, url) candidates from a srcset-like attribute."""
    from urllib.parse import urljoin

    candidates = []
    for item in (srcset or "").split(","):
        parts = item.strip().split()
        if not parts:
            continue

        raw_url = parts[0]
        descriptor = parts[1] if len(parts) > 1 else ""

        try:
            if descriptor.endswith("w"):
                width = int(descriptor[:-1])
            elif descriptor.endswith("x"):
                width = int(float(descriptor[:-1]) * 1000)
            else:
                width = 0
        except ValueError:
            width = 0

        candidates.append((width, urljoin(base_url, raw_url)))

    return candidates


def _diks_figure_image_url(soup, base_url):
    """Return the highest-resolution image from the article's main figure."""
    from urllib.parse import urljoin

    figure = soup.select_one(".diks-figure__image")
    if not figure:
        return ""

    candidates = []

    # The element may itself be an img, or may contain the img/picture.
    elements = [figure] + figure.find_all(["img", "source"])

    for element in elements:
        for attr in ("srcset", "data-srcset"):
            candidates.extend(
                _srcset_candidates(element.get(attr), base_url)
            )

        # Prefer explicit original-image attributes over ordinary src.
        for attr in ("data-original", "data-src", "src"):
            value = element.get(attr)
            if value:
                candidates.append((0, urljoin(base_url, value)))

    if not candidates:
        return ""

    # Use the largest declared source. If there is no width information,
    # preserve DOM order.
    candidates.sort(key=lambda item: item[0], reverse=True)
    return candidates[0][1]


def find_original_image_url(soup, base_url):
    """Select the article's main original image without cropping/resizing."""
    image_url = _diks_figure_image_url(soup, base_url)
    if image_url:
        return image_url

    # Metadata is only a fallback for pages where the main figure is absent.
    from urllib.parse import urljoin

    for attrs in (
        {"property": "og:image"},
        {"name": "twitter:image"},
        {"property": "twitter:image"},
    ):
        image_meta = soup.find("meta", attrs=attrs)
        if image_meta and image_meta.get("content"):
            return urljoin(base_url, image_meta["content"].strip())

    return ""


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

    image_url = find_original_image_url(soup, url)

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
