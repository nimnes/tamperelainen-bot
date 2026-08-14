import os
from dotenv import load_dotenv

load_dotenv()

RSS_URL = "https://www.tamperelainen.fi/feed/rss/"
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY", "")
OLLAMA_URL = os.getenv("OLLAMA_URL", "https://ollama.com/api")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:30b")
OUTPUT_LANGUAGE = os.getenv("OUTPUT_LANGUAGE", "en").lower().strip()
if OUTPUT_LANGUAGE not in {"en", "ru"}:
    raise ValueError("OUTPUT_LANGUAGE must be either en or ru.")
RSS_LIMIT = int(os.getenv("RSS_LIMIT", "20"))
MAX_ARTICLE_CHARS = int(os.getenv("MAX_ARTICLE_CHARS", "16000"))
DB_PATH = os.getenv("DB_PATH", "data/articles.db")
