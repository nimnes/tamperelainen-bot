from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parents[1]
TEXT = (ROOT / "translator.py").read_text(encoding="utf-8")


def test_finnish_admin_terms_constant_exists():
    tree = ast.parse(TEXT)
    assignments = {
        node.targets[0].id
        for node in tree.body
        if isinstance(node, ast.Assign)
        and len(node.targets) == 1
        and isinstance(node.targets[0], ast.Name)
    }
    assert "_FINNISH_ADMIN_TERMS" in assignments


def test_admin_term_helper_can_find_terms():
    namespace = {}
    exec(compile(TEXT, str(ROOT / "translator.py"), "exec"), namespace)
    assert "jaostolle" in namespace["_finnish_admin_terms"](
        "Tampereen yhdyskuntalautakunnan alueellisen ympäristöterveydenhuollon jaostolle"
    )
