from pathlib import Path

TEXT = (Path(__file__).resolve().parents[1] / "translator.py").read_text(encoding="utf-8")


def test_model_native_local_name_rules_are_present():
    assert "canonical Finnish form" in TEXT
    assert "Do not translate, transliterate" in TEXT
    assert "Tampereella -> Tampere" in TEXT
    assert "Lempäälässä -> Lempäälä" in TEXT
    assert "Pirkanmaalla -> Pirkanmaa" in TEXT


def test_major_city_rules_are_present():
    assert "Tampere -> Тампере" in TEXT
    assert "Helsinki -> Хельсинки" in TEXT
    assert "Tampereella -> Тампере" in TEXT
    assert "Helsingissä -> Хельсинки" in TEXT
    assert "Major Finnish cities with established Russian names MUST always use their" in TEXT


def test_model_is_told_not_to_add_wrappers_or_placeholders():
    assert "Do not put square brackets" in TEXT
    assert "placeholder markup" in TEXT
