from unittest.mock import Mock

import pytest

import translator


@pytest.mark.parametrize("source_name", [
    "Digi- ja väestötietovirasto",
    "Digi- ja väestötietoviraston",
    "Digi- ja väestötietovirastossa",
    "DVV",
    "DVV:n",
    "DVV:lle",
])
def test_russian_translation_receives_dvv_rules(monkeypatch, source_name):
    monkeypatch.setattr(translator, "OUTPUT_LANGUAGE", "ru")
    editor = translator.OllamaEditor()
    response = Mock(status_code=200)
    response.json.return_value = {"message": {"content":
        '{"title":"Новости DVV","summary":"Агентство цифровой информации и учёта '
        'населения Финляндии (DVV) сообщило об изменениях.","category":"LOCAL"}'
    }}
    request = Mock(return_value=response)
    monkeypatch.setattr(editor, "_ollama_request", request)

    result = editor.process(source_name, f"{source_name} tiedottaa muutoksista.")

    prompt = request.call_args.args[0]["messages"][1]["content"]
    normalized = " ".join(prompt.split("CATEGORY RULES:")[0].split())
    assert "Digi- ja väestötietovirasto" in normalized
    assert "Агентство цифровой информации и учёта населения Финляндии (DVV)" in normalized
    assert "on first mention; use DVV on subsequent mentions" in normalized
    assert source_name in normalized
    assert "Do not confuse DVV with Migri" in normalized
    assert result["title"] == "Новости DVV"
    assert request.call_count == 1
