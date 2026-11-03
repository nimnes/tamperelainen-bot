from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

import bot
from translator import ModelRequestError


@pytest.fixture
def batch(monkeypatch):
    articles = [SimpleNamespace(url=f"https://example.org/{i}", title=f"Article {i}",
                                published="", description="Source") for i in range(4)]
    monkeypatch.setattr(bot, "init_db", Mock())
    monkeypatch.setattr(bot, "any_processed", lambda: True)
    monkeypatch.setattr(bot, "is_processed", lambda _: False)
    monkeypatch.setattr(bot, "fetch_articles", lambda: list(reversed(articles)))
    monkeypatch.setattr(bot, "fetch_article", lambda *_: {"title": "", "text": "Source"})
    monkeypatch.setattr(bot, "MAX_ARTICLES_PER_RUN", 5)
    editor = Mock()
    editor.process.return_value = {"title": "Title", "summary": "Summary",
                                   "category": "LOCAL", "category_label": "Local"}
    monkeypatch.setattr(bot, "NewsEditor", lambda: editor)
    sent = AsyncMock()
    marked = Mock()
    monkeypatch.setattr(bot, "send_message", sent)
    monkeypatch.setattr(bot, "mark_processed", marked)
    return articles, editor, sent, marked


def test_provider_outage_stops_batch_without_marking_unposted_articles(batch):
    articles, editor, sent, marked = batch
    result = editor.process.return_value
    editor.process.side_effect = [result, ModelRequestError("google HTTP 500")]
    stats = bot.process_once()
    assert (stats.posted, stats.failed, stats.deferred) == (1, 1, 2)
    assert editor.process.call_count == 2
    assert sent.await_count == 1
    marked.assert_called_once_with(articles[0].url, articles[0].title, "")


def test_article_specific_failure_allows_later_articles(batch):
    articles, editor, sent, marked = batch
    result = editor.process.return_value
    editor.process.side_effect = [RuntimeError("Invalid JSON"), result, result, result]
    stats = bot.process_once()
    assert (stats.posted, stats.failed, stats.deferred) == (3, 1, 0)
    assert all(call.args[0] != articles[0].url for call in marked.call_args_list)


def test_delivery_failure_is_not_marked_processed(batch):
    articles, editor, sent, marked = batch
    sent.side_effect = [RuntimeError("Delivery failed"), None, None, None]
    stats = bot.process_once()
    assert (stats.posted, stats.failed) == (3, 1)
    assert all(call.args[0] != articles[0].url for call in marked.call_args_list)


def test_real_batch_limit_defers_remaining_articles(batch, monkeypatch):
    _, editor, _, marked = batch
    monkeypatch.setattr(bot, "MAX_ARTICLES_PER_RUN", 2)
    stats = bot.process_once()
    assert (stats.posted, stats.failed, stats.deferred) == (2, 0, 2)
    assert editor.process.call_count == marked.call_count == 2


def test_actions_outputs_have_real_newlines(tmp_path, monkeypatch):
    path = tmp_path / "outputs"
    monkeypatch.setenv("GITHUB_OUTPUT", str(path))
    bot.write_run_outputs(bot.RunResult(posted=2, failed=1, deferred=3))
    assert path.read_text().splitlines() == [
        "new_articles=2", "failed_articles=1", "deferred_articles=3",
    ]


def test_batch_deadline_defers_without_calling_provider(batch, monkeypatch):
    _, editor, sent, marked = batch
    clock = iter([0, 300])
    monkeypatch.setattr(bot.time, "monotonic", lambda: next(clock))
    stats = bot.process_once()
    assert (stats.posted, stats.failed, stats.deferred) == (0, 0, 4)
    editor.process.assert_not_called()
    sent.assert_not_called()
    marked.assert_not_called()
