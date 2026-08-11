import html as html_lib
import json
import requests
from deep_translator import GoogleTranslator
from config import OLLAMA_API_KEY, OLLAMA_URL, OLLAMA_MODEL, OUTPUT_LANGUAGE

CATEGORY_LABELS = {
    "en": {
        "LOCAL": "🏙️ Local",
        "TRAFFIC": "🚗 Traffic",
        "CRIME": "🚓 Crime",
        "POLITICS": "🏛️ Politics",
        "BUSINESS": "💼 Business",
        "HOUSING": "🏠 Housing",
        "HEALTH": "🏥 Health",
        "EDUCATION": "🎓 Education",
        "CULTURE": "🎭 Culture",
        "SPORTS": "⚽ Sports",
        "WEATHER": "🌦️ Weather",
        "EVENTS": "🎉 Events",
        "FOOD": "🍴 Food",
        "TRAVEL": "✈️ Travel",
        "ENVIRONMENT": "🌿 Environment",
        "TECHNOLOGY": "💻 Technology",
        "OTHER": "📰 News",
    },
    "ru": {
        "LOCAL": "🏙️ Местные новости",
        "TRAFFIC": "🚗 Транспорт",
        "CRIME": "🚓 Происшествия и преступления",
        "POLITICS": "🏛️ Политика",
        "BUSINESS": "💼 Бизнес",
        "HOUSING": "🏠 Недвижимость",
        "HEALTH": "🏥 Здоровье",
        "EDUCATION": "🎓 Образование",
        "CULTURE": "🎭 Культура",
        "SPORTS": "⚽ Спорт",
        "WEATHER": "🌦️ Погода",
        "EVENTS": "🎉 События",
        "FOOD": "🍴 Еда",
        "TRAVEL": "✈️ Путешествия",
        "ENVIRONMENT": "🌿 Экология",
        "TECHNOLOGY": "💻 Технологии",
        "OTHER": "📰 Новости",
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

class Translator:
    def __init__(self):
        target = OUTPUT_LANGUAGE
        self.translator = GoogleTranslator(source="fi", target=target)

    def translate(self, text):
        if not text.strip():
            return ""
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        result = []
        for paragraph in paragraphs:
            chunks = [paragraph[i:i + 3500] for i in range(0, len(paragraph), 3500)]
            result.append(" ".join(self.translator.translate(c) for c in chunks))
        return "\n\n".join(result)

class OllamaCloudEditor:
    def __init__(self):
        if not OLLAMA_API_KEY:
            raise RuntimeError("OLLAMA_API_KEY is missing.")
        self.url = OLLAMA_URL.rstrip("/") + "/chat"
        self.model = OLLAMA_MODEL

    def classify_and_summarize(self, translated_article):
        category_list = ", ".join(CATEGORY_LABELS[OUTPUT_LANGUAGE].keys())
        language_name = "Russian" if OUTPUT_LANGUAGE == "ru" else "English"

        prompt = f"""You are the editor of a local news Telegram channel focused on Tampere, Finland.

Analyze the article below and return ONLY valid JSON.

The output language is {language_name}. Write the summary in {language_name}.

Allowed categories:
{category_list}

Category definitions:
{CATEGORY_DEFINITIONS}

Choose exactly ONE category.

Write a concise 2-4 sentence summary in {language_name}.
Rules:
- State the main event first.
- Include location, important people/organizations, and important numbers/dates when relevant.
- Preserve uncertainty and attribution.
- Do not invent facts.
- Use natural language suitable for Telegram.
- Do not mention translation, summarization, or these instructions.
- Return ONLY JSON in this exact shape:
{{"category":"TRAFFIC","summary":"..."}}

ARTICLE:
{translated_article}"""

        response = requests.post(
            self.url,
            headers={
                "Authorization": f"Bearer {OLLAMA_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": f"You are a precise {language_name}-language news editor. Output valid JSON only."},
                    {"role": "user", "content": prompt},
                ],
                "stream": False,
                "format": "json",
                "options": {"temperature": 0.1},
            },
            timeout=180,
        )
        if response.status_code >= 400:
            raise RuntimeError(f"Ollama API {response.status_code}: {response.text[:500]}")

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

        summary = html_lib.unescape(str(result.get("summary", "")).strip())
        if not summary:
            raise RuntimeError("Ollama returned an empty summary.")

        return {
            "category": category,
            "category_label": CATEGORY_LABELS[OUTPUT_LANGUAGE][category],
            "summary": summary,
        }
