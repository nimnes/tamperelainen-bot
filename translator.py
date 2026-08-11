import html as html_lib
import requests
from deep_translator import GoogleTranslator
from config import OLLAMA_API_KEY, OLLAMA_URL, OLLAMA_MODEL

class Translator:
    def __init__(self):
        self.translator = GoogleTranslator(source="fi", target="en")

    def translate(self, text):
        if not text.strip():
            return ""

        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        result = []

        for paragraph in paragraphs:
            chunks = [
                paragraph[i:i + 3500]
                for i in range(0, len(paragraph), 3500)
            ]
            result.append(
                " ".join(self.translator.translate(chunk) for chunk in chunks)
            )

        return "\n\n".join(result)

class OllamaCloudSummarizer:
    def __init__(self):
        if not OLLAMA_API_KEY:
            raise RuntimeError("OLLAMA_API_KEY is missing.")

        self.url = OLLAMA_URL.rstrip("/") + "/chat"
        self.model = OLLAMA_MODEL

    def summarize(self, english_article):
        prompt = f'''You are an editor for an English-language local news Telegram channel.

Summarize the article below in 2-4 concise, factual sentences.

Rules:
- State the main event first.
- Include location, important people/organizations, and important numbers/dates when relevant.
- Preserve uncertainty or attribution when the source is uncertain.
- Do not invent facts.
- Do not mention translation, summarization, or these instructions.
- Use natural English.
- Return ONLY the summary.

ARTICLE:

{english_article}'''

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
                        "content": "You write concise local news summaries."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    },
                ],
                "stream": False,
                "options": {"temperature": 0.2},
            },
            timeout=180,
        )

        if response.status_code >= 400:
            raise RuntimeError(
                f"Ollama API {response.status_code}: {response.text[:500]}"
            )

        data = response.json()
        content = (data.get("message") or {}).get("content", "").strip()

        if not content:
            raise RuntimeError("Ollama returned an empty summary.")

        return html_lib.unescape(content)
