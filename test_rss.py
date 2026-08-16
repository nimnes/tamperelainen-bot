#!/usr/bin/env python3
"""Run the article pipeline locally without sending anything to Telegram.

Examples:
    python test_rss.py
    python test_rss.py --count 10
    python test_rss.py --count 10 --output test_results.json

The script fetches RSS articles, extracts their Finnish text, runs the normal
Ollama translation/editor, prints the results, and optionally saves them as JSON.
It does not initialize or modify the article database and never imports the
Telegram sender.
"""

import argparse
import json
from datetime import datetime, timezone

from config import MAX_ARTICLE_CHARS
from rss import fetch_articles
from scraper import fetch_article
from translator import OllamaEditor


def run(count: int, output: str | None) -> int:
    articles = fetch_articles()
    if not articles:
        print("No RSS articles were fetched.")
        return 1

    selected = articles[:count]
    print(f"Found {len(articles)} RSS articles; testing {len(selected)} newest article(s).")
    print("Telegram is NOT used. The article database is NOT read or modified.")
    print()

    editor = OllamaEditor()
    results = []

    for index, article in enumerate(selected, start=1):
        print("=" * 72)
        print(f"{index}/{len(selected)}")
        print(f"RSS title: {article.title}")
        print(f"URL:       {article.url}")

        result = {
            "index": index,
            "url": article.url,
            "rss_title": article.title,
            "published": article.published,
            "success": False,
        }

        try:
            extracted = fetch_article(article.url, article.description)
            title_fi = extracted["title"] or article.title
            body_fi = (
                extracted["text"]
                or extracted["description"]
                or article.description
            )[:MAX_ARTICLE_CHARS]

            print(f"Extracted: {len(body_fi)} Finnish characters")
            print()
            print("--- Finnish source ---")
            print(title_fi)
            print(body_fi)
            print()
            print("--- Ollama result ---")

            editorial = editor.process(title_fi, body_fi)

            print(f"Title:    {editorial['title']}")
            print(f"Category: {editorial['category']}")
            print(f"Summary:  {editorial['summary']}")
            print()

            result.update(
                {
                    "success": True,
                    "source_title": title_fi,
                    "source_text": body_fi,
                    "translated": editorial,
                }
            )

        except Exception as exc:
            print(f"ERROR: {exc}")
            result["error"] = str(exc)

        results.append(result)

    successful = sum(1 for item in results if item["success"])
    failed = len(results) - successful

    print("=" * 72)
    print(f"Finished: {successful} successful, {failed} failed.")

    if output:
        payload = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "count_requested": count,
            "count_fetched": len(articles),
            "count_tested": len(selected),
            "successful": successful,
            "failed": failed,
            "results": results,
        }
        with open(output, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
        print(f"Results saved to: {output}")

    return 0 if successful else 1


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Test RSS extraction and Ollama translation without Telegram."
    )
    parser.add_argument(
        "--count",
        type=int,
        default=10,
        help="Number of newest RSS articles to test (default: 10).",
    )
    parser.add_argument(
        "--output",
        metavar="FILE",
        help="Optional JSON file containing source text and Ollama results.",
    )
    args = parser.parse_args()

    if args.count < 1:
        parser.error("--count must be at least 1.")

    return run(args.count, args.output)


if __name__ == "__main__":
    raise SystemExit(main())
