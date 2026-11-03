from datetime import datetime, timezone
from email.utils import format_datetime
from unittest.mock import Mock

import pytest
import requests

import translator
from translator import ModelRequestError, NewsEditor, _retry_delay

PAYLOAD = {"model": "gemma-4-31b-it", "messages": [], "options": {}}


def response(status=200, data=None, headers=None):
    return Mock(status_code=status, headers=headers or {}, json=Mock(return_value=data or {
        "candidates": [{"finishReason": "STOP", "content": {"parts": [{"text": "{}"}]}}]
    }))


@pytest.fixture
def transport(monkeypatch):
    monkeypatch.setattr(translator, "LLM_PROVIDER", "google")
    monkeypatch.setattr(translator, "GOOGLE_API_KEY", "private-key")
    monkeypatch.setattr(translator.random, "uniform", lambda *_: 0)
    clock = [0.0]
    sleeps = []
    monkeypatch.setattr(translator.time, "monotonic", lambda: clock[0])

    def sleep(seconds):
        sleeps.append(seconds)
        clock[0] += seconds

    monkeypatch.setattr(translator.time, "sleep", sleep)
    post = Mock()
    monkeypatch.setattr(translator.requests, "post", post)
    return NewsEditor(), post, sleeps, clock


@pytest.mark.parametrize("status", [408, 429, 500, 502, 503, 504])
def test_recovers_after_multiple_transient_failures(transport, status):
    editor, post, sleeps, _ = transport
    post.side_effect = [response(status), response(status), response(status), response()]
    assert editor._model_request(PAYLOAD)["message"]["content"] == "{}"
    assert sleeps == [5, 10, 20]
    assert post.call_count == 4
    assert all(call.kwargs["timeout"] <= 40 for call in post.call_args_list)


def test_exhaustion_and_safe_diagnostics(transport, capsys):
    editor, post, sleeps, _ = transport
    post.return_value = response(500, {"error": {
        "status": "INTERNAL", "message": "private-key and source article",
    }})
    with pytest.raises(ModelRequestError, match="HTTP 500.*INTERNAL.*exhausted 4") as exc:
        editor._model_request(PAYLOAD)
    logs = capsys.readouterr().out + str(exc.value)
    assert "private-key" not in logs
    assert "source article" not in logs
    assert sleeps == [5, 10, 20]


@pytest.mark.parametrize("status", [400, 401, 403, 404])
def test_permanent_http_errors_are_not_retried(transport, status):
    editor, post, sleeps, _ = transport
    post.return_value = response(status)
    with pytest.raises(ModelRequestError) as exc:
        editor._model_request(PAYLOAD)
    assert exc.value.stop_batch == (status in {401, 403})
    assert post.call_count == 1
    assert sleeps == []


def test_network_errors_back_off_without_logging_exception_details(transport, capsys):
    editor, post, sleeps, _ = transport
    post.side_effect = [requests.exceptions.Timeout("private-key"), response()]
    assert editor._model_request(PAYLOAD)["message"]["content"] == "{}"
    assert sleeps == [5]
    assert "private-key" not in capsys.readouterr().out


def test_retry_after_and_google_retry_info_are_respected(transport):
    editor, post, sleeps, _ = transport
    post.side_effect = [
        response(429, {"error": {"details": [{
            "@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": "25.5s"
        }]}}, {"Retry-After": "15"}),
        response(),
    ]
    editor._model_request(PAYLOAD)
    assert sleeps == [25.5]


def test_long_retry_after_defers_without_retrying_early(transport):
    editor, post, sleeps, _ = transport
    post.return_value = response(429, headers={"Retry-After": "3600"})
    with pytest.raises(ModelRequestError, match="deferred"):
        editor._model_request(PAYLOAD)
    assert post.call_count == 1
    assert sleeps == []


def test_batch_deadline_prevents_additional_requests(transport):
    editor, post, sleeps, clock = transport
    editor.deadline = 4
    post.return_value = response(503)
    with pytest.raises(ModelRequestError, match="deferred"):
        editor._model_request(PAYLOAD)
    assert post.call_count == 1
    assert sleeps == []
    assert post.call_args.kwargs["timeout"] == 4
    clock[0] = 4
    post.reset_mock()
    with pytest.raises(ModelRequestError, match="budget exhausted"):
        editor._model_request(PAYLOAD)
    post.assert_not_called()


def test_retry_after_http_date_and_malformed_headers(transport, monkeypatch):
    class FixedDateTime:
        @staticmethod
        def now(tz):
            return datetime(2026, 11, 3, tzinfo=timezone.utc)

    monkeypatch.setattr(translator, "datetime", FixedDateTime)
    header = format_datetime(datetime(2026, 11, 3, 0, 0, 30, tzinfo=timezone.utc))
    assert _retry_delay(response(429, headers={"Retry-After": header}), 0) == 30
    for header in ["bad date", "-1", "nan"]:
        assert _retry_delay(response(429, headers={"Retry-After": header}), 0) == 5


def test_invalid_json_response_is_retried(transport):
    editor, post, sleeps, _ = transport
    invalid = response()
    invalid.json.side_effect = ValueError("private-key")
    post.side_effect = [invalid, response()]
    assert editor._model_request(PAYLOAD)["message"]["content"] == "{}"
    assert sleeps == [5]


@pytest.mark.parametrize("status,transient", [
    (408, True), (429, True), (500, True), (502, True), (503, True), (504, True),
    (400, False), (401, False), (403, False), (404, False),
])
def test_http_failure_severity_is_classified(transport, status, transient):
    editor, post, _, _ = transport
    post.return_value = response(status)
    with pytest.raises(ModelRequestError) as exc:
        editor._model_request(PAYLOAD, retries=0)
    assert exc.value.transient is transient


def test_exhausted_timeout_is_temporary(transport):
    editor, post, _, _ = transport
    post.side_effect = requests.exceptions.Timeout()
    with pytest.raises(ModelRequestError) as exc:
        editor._model_request(PAYLOAD, retries=0)
    assert exc.value.transient is True


def test_invalid_api_json_remains_an_error(transport):
    editor, post, _, _ = transport
    invalid = response()
    invalid.json.side_effect = ValueError()
    post.return_value = invalid
    with pytest.raises(ModelRequestError) as exc:
        editor._model_request(PAYLOAD, retries=0)
    assert exc.value.transient is False
