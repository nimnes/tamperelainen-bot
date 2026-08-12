import argparse
import asyncio
import html
from email.utils import parsedate_to_datetime

from config import MAX_ARTICLE_CHARS, OUTPUT_LANGUAGE
from database import init_db, is_processed, mark_processed, any_processed
from rss import fetch_articles
from scraper import fetch_article
from translator import OllamaEditor
from telegram_sender import send_message


def format_date(value):
    if not value:
        return ""
    try:
        dt = parsedate_to_datetime(value)
        if OUTPUT_LANGUAGE == "ru":
            months = [
                "января", "февраля", "марта", "апреля", "мая", "июня",
                "июля", "августа", "сентября", "октября", "ноября", "декабря",
            ]
            return f"{dt.day} {months[dt.month - 1]} {dt.year}, {dt:%H:%M}"
        months = [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December",
        ]
        return f"{months[dt.month - 1]} {dt.day}, {dt.year}, {dt:%H:%M}"
    except (TypeError, ValueError, IndexError):
        return value


def build_message(article, editorial):
    published = format_date(article.published)
    original_label = (
        "🔗 Читать оригинал статьи"
        if OUTPUT_LANGUAGE == "ru"
        else "🔗 Read original article"
    )
    return (
        f"{editorial['category_label']}\n\n"
        f"<b>{html.escape(editorial['title'])}</b>\n\n"
        f"{html.escape(editorial['summary'])}\n\n"
        f"🕒 {html.escape(published)}\n\n"
        f'<a href="{html.escape(article.url, quote=True)}">{original_label}</a>'
    )


def process_once(test=False):
    init_db()
    articles = fetch_articles()
    print(f"Found {len(articles)} RSS articles.")

    if not any_processed():
        print("No processed-article history found. Creating initial RSS baseline.")
        for article in articles:
            mark_processed(article.url, article.title, article.published)
        print(f"Baseline saved: {len(articles)} existing articles will not be posted.")
        return

    editor = OllamaEditor()
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
            editorial = editor.process(title_fi, body_fi)
            message = build_message(article, editorial)

            if test:
                print("\n--- TEST MESSAGE ---")
                print(message)
                print("--- END TEST MESSAGE ---")
            else:
                asyncio.run(
                    send_message(
                        message,
                        image_url=extracted.get("image_url") or None,
                    )
                )
                print(f"Sent as {editorial['category']}.")
                mark_processed(article.url, article.title, article.published)
                print("Saved article as processed.")

        except Exception as exc:
            print(f"ERROR processing {article.url}: {exc}")

    print(f"New articles processed: {new_count}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", action="store_true")
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    if not (args.test or args.once):
        parser.error("Use --test or --once.")
    process_once(test=args.test)
