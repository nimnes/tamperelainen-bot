import html as html_lib
import json

import requests

from config import OLLAMA_API_KEY, OLLAMA_URL, OLLAMA_MODEL, OUTPUT_LANGUAGE

CATEGORY_LABELS = {
    "en": {
        "LOCAL": "🏙️ Local", "TRAFFIC": "🚗 Traffic", "CRIME": "🚓 Crime",
        "POLITICS": "🏛️ Politics", "BUSINESS": "💼 Business", "HOUSING": "🏠 Housing",
        "HEALTH": "🏥 Health", "EDUCATION": "🎓 Education", "CULTURE": "🎭 Culture",
        "SPORTS": "⚽ Sports", "WEATHER": "🌦️ Weather", "EVENTS": "🎉 Events",
        "FOOD": "🍴 Food", "TRAVEL": "✈️ Travel", "ENVIRONMENT": "🌿 Environment",
        "TECHNOLOGY": "💻 Technology", "OTHER": "📰 News",
    },
    "ru": {
        "LOCAL": "🏙️ Местные новости", "TRAFFIC": "🚗 Транспорт",
        "CRIME": "🚓 Происшествия и преступления", "POLITICS": "🏛️ Политика",
        "BUSINESS": "💼 Бизнес", "HOUSING": "🏠 Недвижимость", "HEALTH": "🏥 Здоровье",
        "EDUCATION": "🎓 Образование", "CULTURE": "🎭 Культура", "SPORTS": "⚽ Спорт",
        "WEATHER": "🌦️ Погода", "EVENTS": "🎉 События", "FOOD": "🍴 Еда",
        "TRAVEL": "✈️ Путешествия", "ENVIRONMENT": "🌿 Экология",
        "TECHNOLOGY": "💻 Технологии", "OTHER": "📰 Новости",
    },
}

CATEGORY_DEFINITIONS = """LOCAL = general local news that does not fit a more specific category
TRAFFIC = roads, public transport, accidents, parking, cycling infrastructure
CRIME = police, crimes, arrests, courts, suspected offences
POLITICS = politicians, elections, city council, public policy
BUSINESS = companies, jobs, commerce, economy, entrepreneurship
HOUSING = homes, apartments, residential construction, rents, real estate
HEALTH = hospitals, healthcare, diseases, public health
EDUCATION = schools, universities, students, teaching
CULTURE = arts, music, theatre, museums, books, film
SPORTS = sports, teams, athletes, competitions
WEATHER = weather, forecasts, storms, seasonal conditions
EVENTS = festivals, concerts, fairs and other events
FOOD = restaurants, food, cooking, groceries
TRAVEL = travel and tourism
ENVIRONMENT = nature, climate, pollution, conservation
TECHNOLOGY = technology, software, digital services
OTHER = none of the above"""


class OllamaEditor:
    """Translate, summarize and classify the original Finnish article in one request."""

    def __init__(self):
        if not OLLAMA_API_KEY:
            raise RuntimeError("OLLAMA_API_KEY is missing.")
        self.url = OLLAMA_URL.rstrip("/") + "/chat"
        self.model = OLLAMA_MODEL

    def process(self, title_fi, article_fi):
        language = "Russian" if OUTPUT_LANGUAGE == "ru" else "English"
        prompt = f"""You are a professional local-news editor and translator.

The source article is Finnish. Create a natural {language} version for readers
interested in Tampere, Finland.

Return ONLY valid JSON in exactly this shape:
{{"title":"...","summary":"...","category":"LOCAL"}}

Rules:
- Understand the Finnish text before writing; do not translate word-for-word.
- Write a natural journalistic headline in {language}.
- Write a concise 2-4 sentence summary in {language}.
- Preserve names, places, organizations, numbers, dates and times accurately.
- Preserve uncertainty and attribution; never turn allegations into facts.
- Do not invent, infer, or embellish facts.
- The headline should be informative, not clickbait.
- Do not include HTML tags.
- Choose exactly one category from the list below.

Categories:
{CATEGORY_DEFINITIONS}

Finnish headline:
{title_fi}

Finnish article:
{article_fi}
"""

        response = requests.post(
            self.url,
            headers={
                "Authorization": f"Bearer {OLLAMA_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            f"You are a precise Finnish-to-{language} news translator "
                            "and editor. Return valid JSON only."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                "stream": False,
                "format": "json",
                "options": {"temperature": 0.15},
            },
            timeout=180,
        )
        if response.status_code >= 400:
            raise RuntimeError(
                f"Ollama API {response.status_code}: {response.text[:500]}"
            )

        content = (response.json().get("message") or {}).get("content", "").strip()
        if not content:
            raise RuntimeError("Ollama returned an empty editor response.")

        try:
            result = json.loads(content)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Ollama returned invalid JSON: {content}") from exc

        category = str(result.get("category", "OTHER")).upper().strip()
        if category not in CATEGORY_LABELS[OUTPUT_LANGUAGE]:
            category = "OTHER"

        title = html_lib.unescape(str(result.get("title", "")).strip())
        summary = html_lib.unescape(str(result.get("summary", "")).strip())
        if not title or not summary:
            raise RuntimeError("Ollama returned an empty title or summary.")

        return {
            "title": title,
            "summary": summary,
            "category": category,
            "category_label": CATEGORY_LABELS[OUTPUT_LANGUAGE][category],
        }
