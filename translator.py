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
        "CRIME": "🚓 Происшествия", "POLITICS": "🏛️ Политика",
        "BUSINESS": "💼 Бизнес", "HOUSING": "🏠 Недвижимость", "HEALTH": "🏥 Здоровье",
        "EDUCATION": "🎓 Образование", "CULTURE": "🎭 Культура", "SPORTS": "⚽ Спорт",
        "WEATHER": "🌦️ Погода", "EVENTS": "🎉 События", "FOOD": "🍴 Еда",
        "TRAVEL": "✈️ Путешествия", "ENVIRONMENT": "🌿 Экология",
        "TECHNOLOGY": "💻 Технологии", "OTHER": "📰 Новости",
    },
}

CATEGORY_DEFINITIONS = """LOCAL = general local news that does not fit any more specific category
TRAFFIC = roads, public transport, traffic changes, parking, cycling infrastructure and traffic accidents
CRIME = police, criminal investigations, arrests, courts, fires, rescue services and other incidents
POLITICS = politicians, elections, city council, municipal decisions and public policy
BUSINESS = companies, jobs, shops, commerce, economy and entrepreneurship
HOUSING = homes, apartments, residential construction, rents and real estate
HEALTH = hospitals, healthcare, diseases and public health
EDUCATION = schools, universities, students and teaching
CULTURE = arts, music, theatre, museums, books and film
SPORTS = sports, teams, athletes and competitions
WEATHER = weather, forecasts, storms and seasonal conditions
EVENTS = festivals, concerts, fairs and other public events
FOOD = restaurants, food, cooking and groceries
TRAVEL = travel and tourism
ENVIRONMENT = nature, climate, pollution and conservation
TECHNOLOGY = technology, software and digital services
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
{{"title":"...","summary":"...","category":"<CATEGORY>"}}

TRANSLATION RULES:
- Understand the Finnish text before writing; do not translate word-for-word.
- Write a natural, concise journalistic headline in {language}.
- Write a concise 2-4 sentence summary in {language}.
- Do not invent, infer, embellish or omit important facts.
- Preserve uncertainty and attribution; never turn allegations or speculation into facts.
- Preserve numbers, dates, times and factual details accurately.

PROPER-NAME AND PLACE-NAME RULES:
- NEVER translate or alter people's names. Keep the original Finnish spelling,
  including ä, ö, å and other diacritics.
- NEVER translate Finnish street, road, square, park, neighborhood, district,
  building, venue or local geographic names. Keep names such as Hämeenkatu,
  Aleksanterinkatu, Pyynikintie and Näsijärvi in their original Finnish form.
- Keep local business, organization and institution names in their original form
  unless there is a clearly established official name in {language}.
- Major Finnish cities may use their well-established {language} names when one
  exists (for example Tampere -> Tampere in English, Tampere -> Тампере in Russian;
  Helsinki -> Helsinki in English, Helsinki -> Хельсинки in Russian).
- Smaller places should normally remain in Finnish unless there is a widely
  established standard name in {language}.
- Do not transliterate Finnish proper names merely to make them look local.
- If unsure whether a word is a proper name, KEEP THE ORIGINAL FINNISH FORM.
- Street suffixes such as -katu, -tie and -kuja must remain unchanged.

CATEGORY RULES:
- First identify the MAIN SUBJECT of the article.
- Choose the MOST SPECIFIC category that describes the main subject.
- Do NOT choose LOCAL merely because the article is about Tampere or another
  Finnish city. LOCAL is a FALLBACK category only when no specific category fits.
- A mention of a category does not make it the category. Classify by the main
  focus of the story.
- Examples: a tram or road story -> TRAFFIC; police investigation -> CRIME;
  restaurant -> FOOD; school -> EDUCATION; sports match -> SPORTS; city council
  decision -> POLITICS; theatre/concert -> CULTURE; apartment development -> HOUSING.
- Choose exactly ONE category from this list:

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
                            "and editor. Return valid JSON only. Preserve proper names. "
                            "Choose the most specific category, using LOCAL only as a fallback."
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
