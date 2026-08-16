from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEXT = (ROOT / "translator.py").read_text(encoding="utf-8")


def test_major_city_translation_rules_are_explicit():
    for source, target in [
        ("Tampere", "Тампере"),
        ("Helsinki", "Хельсинки"),
        ("Espoo", "Эспоо"),
        ("Vantaa", "Вантаа"),
        ("Turku", "Турку"),
        ("Oulu", "Оулу"),
        ("Lahti", "Лахти"),
        ("Jyväskylä", "Ювяскюля"),
        ("Kuopio", "Куопио"),
        ("Rovaniemi", "Рованиеми"),
        ("Hämeenlinna", "Хямеэнлинна"),
    ]:
        assert f"{source} -> {target}" in TEXT


def test_city_case_normalization_is_explicit():
    assert "Tampereella -> Тампере" in TEXT
    assert "Tampereen -> Тампере" in TEXT
    assert "Helsingissä -> Хельсинки" in TEXT
    assert "Helsingin -> Хельсинки" in TEXT
