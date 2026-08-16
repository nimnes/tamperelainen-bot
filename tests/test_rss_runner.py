from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parents[1]
TEXT = (ROOT / "test_rss.py").read_text(encoding="utf-8")


def test_local_runner_does_not_use_telegram_or_database():
    tree = ast.parse(TEXT)
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module or "")
    assert not any("telegram" in name.lower() for name in imports)
    assert not any("database" in name.lower() for name in imports)


def test_local_runner_uses_real_pipeline_components():
    assert "from rss import fetch_articles" in TEXT
    assert "from scraper import fetch_article" in TEXT
    assert "from translator import OllamaEditor" in TEXT
    assert "editor.process(title_fi, body_fi)" in TEXT


def test_local_runner_never_sends_messages():
    assert "send_message" not in TEXT
    assert "TELEGRAM" not in TEXT


def test_local_runner_does_not_mark_articles_processed():
    assert "mark_processed" not in TEXT
    assert "init_db" not in TEXT
