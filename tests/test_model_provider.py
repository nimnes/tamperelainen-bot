from unittest.mock import Mock, patch

import pytest

from model_provider import build_request, normalize_response
from translator import NewsEditor

PAYLOAD = {"model": "gemma-4-31b-it", "think": False, "format": "json",
           "messages": [{"role": "system", "content": "Return JSON."},
                        {"role": "user", "content": "Suomalainen artikkeli"}],
           "options": {"temperature": 0.1, "num_predict": 1100}}


def test_google_wire_format_and_secret_header():
    url, headers, body = build_request("google", "https://generativelanguage.googleapis.com/v1beta", "secret", PAYLOAD)
    assert url.endswith('/models/gemma-4-31b-it:generateContent')
    assert 'secret' not in url
    assert headers == {'x-goog-api-key': 'secret'}
    assert body['systemInstruction']['parts'][0]['text'] == 'Return JSON.'
    assert body['contents'][0]['parts'][0]['text'] == 'Suomalainen artikkeli'
    assert body['generationConfig']['maxOutputTokens'] == 1100
    assert 'format' not in body and 'think' not in body


def test_google_discards_thinking_and_rejects_partial_or_blocked_output():
    for reason in ['STOP', 'MAX_TOKENS', 'SAFETY']:
        response = normalize_response('google', {'candidates': [{'finishReason': reason,
            'content': {'parts': [{'text': 'private reasoning', 'thought': True}, {'text': '{"title":"ok"}'}]}}]})
        assert response['message']['content'] == ('{"title":"ok"}' if reason == 'STOP' else '')
    assert normalize_response('google', {'promptFeedback': {'blockReason': 'SAFETY'}})['message']['content'] == ''


def test_ollama_format_is_preserved():
    url, headers, body = build_request('ollama', 'https://ollama.com/api', 'ollama-key', PAYLOAD)
    assert url == 'https://ollama.com/api/chat'
    assert headers['Authorization'] == 'Bearer ollama-key'
    assert body == PAYLOAD
    response = {'message': {'content': '{}'}}
    assert normalize_response('ollama', response) == response


def test_missing_google_key_and_invalid_provider_fail_before_request():
    with pytest.raises(ValueError, match='GOOGLE_API_KEY'):
        build_request('google', 'https://example.org', '', PAYLOAD)
    with pytest.raises(ValueError, match='LLM_PROVIDER'):
        build_request('typo', 'https://example.org', 'key', PAYLOAD)


@patch('translator.time.sleep')
@patch('translator.requests.post')
def test_transient_http_failure_retried_without_leaking_key(post, sleep):
    with patch('translator.GOOGLE_API_KEY', 'test'):
        editor = NewsEditor()
    editor.key = 'secret'
    post.side_effect = [Mock(status_code=503), Mock(status_code=200, json=lambda: {
        'candidates': [{'finishReason': 'STOP', 'content': {'parts': [{'text': '{}'}]}}]})]
    assert editor._model_request(PAYLOAD)['message']['content'] == '{}'
    assert post.call_count == 2
    assert post.call_args.kwargs['allow_redirects'] is False
    post.side_effect = None
    post.return_value = Mock(status_code=403)
    with pytest.raises(RuntimeError, match='google HTTP 403') as exc:
        editor._model_request(PAYLOAD)
    assert 'secret' not in str(exc.value)


@pytest.mark.parametrize('provider', ['google', 'ollama'])
@patch('translator.requests.post')
def test_editor_translation_and_admin_repair_work_with_both_providers(post, provider):
    import json
    with patch('translator.GOOGLE_API_KEY', 'test'):
        editor = NewsEditor()
    editor.provider = provider
    editor.key = 'test'
    editor.url = 'https://generativelanguage.googleapis.com/v1beta' if provider == 'google' else 'https://ollama.com/api'
    editor.model = 'gemma-4-31b-it' if provider == 'google' else 'gemma4:31b-cloud'
    replies = [
        {'title': 'Решение', 'summary': 'kaupunginvaltuusto принял решение.', 'category': 'POLITICS'},
        {'title': 'Решение совета', 'summary': 'Городской совет принял решение.'},
    ]
    def respond(*args, **kwargs):
        content = json.dumps(replies.pop(0), ensure_ascii=False)
        envelope = {'message': {'content': content}} if provider == 'ollama' else {
            'candidates': [{'finishReason': 'STOP', 'content': {'parts': [{'text': content}]}}]}
        return Mock(status_code=200, json=lambda: envelope)
    post.side_effect = respond
    with patch('translator.OUTPUT_LANGUAGE', 'ru'):
        result = editor.process('Valtuuston päätös', 'Kaupunginvaltuusto päätti asiasta.')
    assert result['title'] == 'Решение совета'
    assert result['summary'] == 'Городской совет принял решение.'
    assert result['category'] == 'POLITICS'
    assert post.call_count == 2


def test_editor_fails_early_when_google_key_missing():
    with patch('translator.LLM_PROVIDER', 'google'), patch('translator.GOOGLE_API_KEY', ''):
        with pytest.raises(ValueError, match='GOOGLE_API_KEY'):
            NewsEditor()
