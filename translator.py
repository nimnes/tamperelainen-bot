import html as html_lib
import json
import requests
from deep_translator import GoogleTranslator
from config import OLLAMA_API_KEY, OLLAMA_URL, OLLAMA_MODEL

CATEGORIES = {
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
}

class Translator:
    def __init__(self):
        self.translator = GoogleTranslator(source="fi", target="ru")

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

    def classify_and_summarize(self, russian_article):
        allowed = ", ".join(CATEGORIES)
        prompt = f"""Ты редактор русскоязычного Telegram-канала с местными новостями Тампере, Финляндия.

Проанализируй статью и верни ТОЛЬКО корректный JSON.

Допустимые категории: {allowed}

Выбери ровно одну:
LOCAL = общие местные новости, если статья не подходит к более конкретной категории
TRAFFIC = дороги, общественный транспорт, ДТП, парковка, велосипедная инфраструктура
CRIME = полиция, преступления, задержания, суды, предполагаемые правонарушения
POLITICS = политики, выборы, городской совет, государственная и муниципальная политика
BUSINESS = компании, работа, торговля, экономика, предпринимательство
HOUSING = жильё, квартиры, жилое строительство, аренда, недвижимость
HEALTH = больницы, медицина, заболевания, общественное здоровье
EDUCATION = школы, университеты, студенты, обучение
CULTURE = искусство, музыка, театр, музеи, книги, кино
SPORTS = спорт, команды, спортсмены, соревнования
WEATHER = погода, прогнозы, штормы, сезонные погодные условия
EVENTS = фестивали, концерты, ярмарки и другие мероприятия
FOOD = рестораны, продукты, еда, кулинария
TRAVEL = путешествия и туризм
ENVIRONMENT = природа, климат, загрязнение, охрана окружающей среды
TECHNOLOGY = технологии, программное обеспечение, цифровые сервисы
OTHER = если ни одна категория не подходит

Также напиши краткое резюме статьи на русском языке в 2–4 предложениях.
Правила:
- Сначала сообщи главное событие.
- Указывай место, важных людей и организации, числа и даты, если они важны.
- Сохраняй неопределённость и указание источника информации.
- Не придумывай факты.
- Используй естественный современный русский язык, подходящий для Telegram.
- Не упоминай перевод, суммаризацию или эти инструкции.
- Верни ТОЛЬКО JSON следующего вида:
{{"category":"TRAFFIC","summary":"..."}}

СТАТЬЯ:
{russian_article}"""

        response = requests.post(
            self.url,
            headers={"Authorization": f"Bearer {OLLAMA_API_KEY}", "Content-Type": "application/json"},
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": "Ты точный редактор новостей. Возвращай только корректный JSON."},
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
        if category not in CATEGORIES:
            category = "OTHER"

        summary = html_lib.unescape(str(result.get("summary", "")).strip())
        if not summary:
            raise RuntimeError("Ollama returned an empty summary.")

        return {
            "category": category,
            "category_label": CATEGORIES[category],
            "summary": summary,
        }
