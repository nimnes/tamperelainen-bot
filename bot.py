import argparse
import asyncio
import html

from config import MAX_ARTICLE_CHARS
from database import init_db, is_processed, mark_processed
from rss import fetch_articles
from scraper import fetch_article
from translator import Translator, OllamaCloudSummarizer
from telegram_sender import send_message

def build_message(article, title_en, summary_en):
    return (
        f"🇬🇧 <b>{html.escape(title_en)}</b>\n\n"
        f"{html.escape(summary_en)}\n\n"
        f"📰 {html.escape(article.category or 'News')}\n"
        f"🕒 {html.escape(article.published or '')}\n\n"
        f'<a href="{html.escape(article.url, quote=True)}">'
        f"🔗 Read original article</a>"
    )

def process_once(test=False):
    init_db()
    articles = fetch_articles()
    print(f"Found {len(articles)} RSS articles.")

    translator = Translator()
    summarizer = OllamaCloudSummarizer()
    new_count = 0

    for article in reversed(articles):
        if is_processed(article.url):
            continue

        new_count += 1
        print(f"NEW: {article.title}\n{article.url}")

        try:
            extracted = fetch_article(article.url, article.description)
            title_fi = extracted["title"] or article.title
            body_fi = (
                extracted["text"]
                or extracted["description"]
                or article.description
            )[:MAX_ARTICLE_CHARS]

            print(f"Extracted {len(body_fi)} Finnish chars.")

            title_en = translator.translate(title_fi)
            body_en = translator.translate(body_fi)
            summary = summarizer.summarize(body_en)

            message = build_message(article, title_en, summary)

            if test:
                print("\n--- TEST MESSAGE ---")
                print(message)
                print("--- END TEST MESSAGE ---")
            else:
                asyncio.run(send_message(message))
                print("Sent.")

            mark_processed(article.url, article.title, article.published)

        except Exception as exc:
            print(f"ERROR: {exc}")

    print(f"New articles processed: {new_count}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", action="store_true")
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()

    if not (args.test or args.once):
        parser.error("Use --test or --once. Continuous hosting is handled by GitHub Actions.")

    process_once(test=args.test)
