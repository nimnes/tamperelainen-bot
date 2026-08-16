from pathlib import Path

TEXT = (Path(__file__).resolve().parents[1] / "translator.py").read_text(encoding="utf-8")


def test_unused_translation_helpers_are_removed():
    assert "def _mixed_script_words" not in TEXT
    assert "def _summary_needs_expansion" not in TEXT
