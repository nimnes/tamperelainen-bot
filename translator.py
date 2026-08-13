import html as html_lib
import json
import re
import requests

from config import OLLAMA_API_KEY, OLLAMA_URL, OLLAMA_MODEL, OUTPUT_LANGUAGE

CATEGORY_LABELS = {
    "en": {
        "LOCAL": "🏙️ Local", "TRAFFIC": "🚗 Traffic", "CRIME": "🚓 Incidents",
        "POLITICS": "🏛️ Politics", "BUSINESS": "💼 Business", "HOUSING": "🏠 Housing",
        "HEALTH": "🏥 Health", "EDUCATION": "🎓 Education", "CULTURE": "🎭 Culture",
        "SPORTS": "⚽ Sports", "WEATHER": "🌦️ Weather", "EVENTS": "🎉 Events",
        "FOOD": "🍴 Food", "TRAVEL": "✈️ Travel", "ENVIRONMENT": "🌿 Environment",
        "TECHNOLOGY": "💻 Technology", "OTHER": "📰 News",
    },
    "ru": {
        "LOCAL": "🏙️ Местные новости", "TRAFFIC": "🚗 Транспорт", "CRIME": "🚓 Происшествия",
        "POLITICS": "🏛️ Политика", "BUSINESS": "💼 Бизнес", "HOUSING": "🏠 Недвижимость",
        "HEALTH": "🏥 Здоровье", "EDUCATION": "🎓 Образование", "CULTURE": "🎭 Культура",
        "SPORTS": "⚽ Спорт", "WEATHER": "🌦️ Погода", "EVENTS": "🎉 События",
        "FOOD": "🍴 Еда", "TRAVEL": "✈️ Путешествия", "ENVIRONMENT": "🌿 Экология",
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

# These are the only Finnish city names that the model is explicitly allowed
# to render using an established Russian/English form. Local names are handled
# separately and are protected by _protect_local_names().
MAJOR_CITY_TRANSLATIONS = {
    "en": {
        "Tampere": "Tampere", "Helsinki": "Helsinki", "Turku": "Turku",
        "Espoo": "Espoo", "Vantaa": "Vantaa", "Oulu": "Oulu",
        "Lahti": "Lahti", "Jyväskylä": "Jyväskylä",
    },
    "ru": {
        "Tampere": "Тампере", "Helsinki": "Хельсинки", "Turku": "Турку",
        "Espoo": "Эспоо", "Vantaa": "Вантаа", "Oulu": "Оулу",
        "Lahti": "Лахти", "Jyväskylä": "Ювяскюля",
    },
}

# Known Tampere-area names. This is intentionally small; the suffix patterns
# below cover many additional Finnish street/locality names without requiring
# an ever-growing dictionary.
KNOWN_LOCAL_NAMES = [
    "Tullin", "Koskipuisto", "Hervannan Duo", "Hämeenkatu", "Aleksanterinkatu",
    "Pyynikintie", "Tesoman valtatie", "Sammonkatu", "Itsenäisyydenkatu",
    "Kalevantie", "Teiskontie", "Rantaväylä", "Näsijärvi", "Pyynikki",
    "Hervanta", "Tesoma", "Kaleva", "Tammela", "Amuri", "Pispala", "Kaukajärvi",
    "Lielahti", "Nekala", "Hatanpää", "Viinikka", "Rahola", "Linnainmaa",
    "Hervannan valtaväylä", "Tampereen Ratikka",
]

# Finnish local names frequently contain these suffixes. If a word looks like
# such a name, protect it from translation. The rule is conservative and only
# applies to words beginning with a capital letter or known multiword names.
LOCAL_NAME_SUFFIXES = (
    "katu", "tie", "kuja", "väylä", "silta", "aukio", "puisto", "ranta",
    "järvi", "mäki", "niemi", "lahti", "koski", "tori", "asema", "hall",
)


def _protect_local_names(text):
    """Replace local Finnish names with opaque placeholders before Ollama.

    This is deliberately done before the model sees the text. Prompt-only
    instructions are not sufficient for names such as Koskipuisto, which can
    look like an ordinary Finnish compound word to a language model.
    """
    replacements = {}
    protected = text

    candidates = sorted(KNOWN_LOCAL_NAMES, key=len, reverse=True)
    if candidates:
        pattern = re.compile(
            r"(?<![\wÅÄÖåäö])(?:" + "|".join(re.escape(x) for x in candidates) + r")(?![\wÅÄÖåäö])",
            re.IGNORECASE,
        )

        def replace_known(match):
            token = f"[[[LOCAL_NAME_{len(replacements)}]]]"
            replacements[token] = match.group(0)
            return token

        protected = pattern.sub(replace_known, protected)

    # Protect likely Finnish street/locality names not already covered by the
    # dictionary. Do this after known names so placeholders are not re-matched.
    suffix_pattern = re.compile(
        r"\b([A-ZÅÄÖ][\wÅÄÖåäö-]{2,}(?:" + "|".join(re.escape(s) for s in LOCAL_NAME_SUFFIXES) + r"))\b"
    )

    def replace_suffix(match):
        token = f"[[[LOCAL_NAME_{len(replacements)}]]]"
        replacements[token] = match.group(1)
        return token

    protected = suffix_pattern.sub(replace_suffix, protected)
    return protected, replacements


def _restore_local_names(text, replacements):
    for token, original in replacements.items():
        text = text.replace(token, original)
    return text



_CYRILLIC_RE = re.compile(r"[А-Яа-яЁё]")
_LATIN_RE = re.compile(r"[A-Za-z]")

def _mixed_script_words(text):
    words = re.findall(r"[A-Za-zА-Яа-яЁёÀ-ÖØ-öø-ÿĀ-ž'-]+", text)
    return [w for w in words if _CYRILLIC_RE.search(w) and _LATIN_RE.search(w)]


class OllamaEditor:
    """Translate, summarize and classify the original Finnish article in one request."""

    def __init__(self):
        if not OLLAMA_API_KEY:
            raise RuntimeError("OLLAMA_API_KEY is missing.")
        self.url = OLLAMA_URL.rstrip("/") + "/chat"
        self.model = OLLAMA_MODEL

    def _repair_mixed_scripts(self, title, summary):
        if OUTPUT_LANGUAGE != "ru":
            return title, summary

        def repair(text):
            suspicious = _mixed_script_words(text)
            if not suspicious:
                return text

            prompt = f"""Fix accidental Latin/Cyrillic mixing in this Russian news text.

Suspicious words: {", ".join(suspicious)}

Rules:
- Fix only accidental mixed-script Russian words.
- Russian words must use Cyrillic.
- Never translate, transliterate or alter proper names.
- Never alter Finnish place names, street names, businesses, venues, brands,
  abbreviations, URLs, numbers, or intentionally Latin text.
- Keep all facts, meaning and punctuation unchanged.
- Return ONLY the corrected text.

Text:
{text}
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
                                "You are a Russian proofreader. Fix only "
                                "accidental Latin/Cyrillic mixing and never "
                                "alter proper names."
                            ),
                        },
                        {"role": "user", "content": prompt},
                    ],
                    "stream": False,
                    "options": {"temperature": 0.0},
                },
                timeout=120,
            )
            if response.status_code >= 400:
                raise RuntimeError(
                    f"Ollama script-correction API {response.status_code}: "
                    f"{response.text[:500]}"
                )

            corrected = (
                (response.json().get("message") or {})
                .get("content", "")
                .strip()
            )
            if not corrected:
                raise RuntimeError("Ollama returned an empty script correction.")

            remaining = _mixed_script_words(corrected)
            if remaining:
                raise RuntimeError(
                    "Ollama script correction still contains mixed-script words: "
                    + ", ".join(remaining)
                )
            return corrected

        return repair(title), repair(summary)

    def process(self, title_fi, article_fi):
        language = "Russian" if OUTPUT_LANGUAGE == "ru" else "English"
        protected_title, title_names = _protect_local_names(title_fi)
        protected_article, article_names = _protect_local_names(article_fi)
        replacements = {**title_names, **article_names}

        prompt = f"""You are a professional Finnish-to-{language} local-news translator and editor.

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
- Preserve numbers, dates, times, measurements and factual relationships accurately.

PROPER-NAME RULES — STRICT:
- Finnish local proper names are protected in the source using tokens like
  [[[LOCAL_NAME_0]]]. NEVER translate, transliterate, modify or omit these tokens.
  Copy every protected token exactly into the corresponding place in your output.
- After the output is generated, protected tokens will be replaced with their
  original Finnish names. Therefore, do not try to make them readable yourself.
- NEVER translate or alter people's names. Keep original spelling and diacritics.
- NEVER translate Finnish street, road, square, park, neighborhood, district,
  stop, station, building, venue or local geographic names.
- NEVER translate a Finnish local compound name merely because it looks like an
  ordinary Finnish word. For example, Koskipuisto is a proper place name, not
  something to translate as "Rapids Park".
- Keep local businesses, organizations and institutions in their original form
  unless there is a clearly established official {language} name.
- Only major Finnish cities may use an established {language} form. Do not
  translate smaller localities unless the form is genuinely standard.
- If unsure whether a name has an established {language} form, keep Finnish.
- Keep Finnish street suffixes such as -katu, -tie, -kuja, -väylä, -puisto and
  -järvi unchanged when they are part of a local proper name.

Examples for Russian:
Tampere -> Тампере
Helsinki -> Хельсинки
Tullin -> Tullin
Koskipuisto -> Koskipuisto
Hervannan Duo -> Hervannan Duo
Hämeenkatu -> Hämeenkatu
Pyynikintie -> Pyynikintie
Näsijärvi -> Näsijärvi

CATEGORY RULES:
- First identify the MAIN SUBJECT of the article.
- Choose the MOST SPECIFIC category that describes the main subject.
- Do NOT choose LOCAL merely because the article is about Tampere or another
  Finnish city. LOCAL is a FALLBACK category only when no specific category fits.
- A mention of a category does not make it the category; classify by the main focus.
- Examples: tram/road story -> TRAFFIC; police/fire/rescue -> CRIME; restaurant -> FOOD;
  school -> EDUCATION; sports match -> SPORTS; city council decision -> POLITICS;
  theatre/concert -> CULTURE; apartment development -> HOUSING.
- Choose exactly ONE category from this list:

{CATEGORY_DEFINITIONS}

Finnish headline:
{protected_title}

Finnish article:
{protected_article}
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
                            "and editor. Protected local-name tokens are immutable. "
                            "Return valid JSON only."
                        ),
                    },
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

        title = html_lib.unescape(str(result.get("title", "")).strip())
        summary = html_lib.unescape(str(result.get("summary", "")).strip())
        if not title or not summary:
            raise RuntimeError("Ollama returned an empty title or summary.")

        title, summary = self._repair_mixed_scripts(title, summary)

        title = _restore_local_names(title, replacements)
        summary = _restore_local_names(summary, replacements)

        return {
            "title": title,
            "summary": summary,
            "category": category,
            "category_label": CATEGORY_LABELS[OUTPUT_LANGUAGE][category],
        }
