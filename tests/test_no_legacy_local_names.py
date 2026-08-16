from pathlib import Path

TEXT = (Path(__file__).resolve().parents[1] / "translator.py").read_text(encoding="utf-8")


def test_legacy_hardcoded_local_name_list_is_removed():
    assert "KNOWN_LOCAL_NAMES" not in TEXT


def test_legacy_placeholder_implementation_is_removed():
    assert "_protect_local_names" not in TEXT
    assert "_restore_local_names" not in TEXT
    assert "protected_title" not in TEXT
    assert "protected_article" not in TEXT
    assert "LOCAL_NAME_N" not in TEXT
    assert "[[[LOCAL_NAME" not in TEXT
