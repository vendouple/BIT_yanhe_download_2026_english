"""Fail when a user-visible GUI literal still renders with Chinese text."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import i18n  # noqa: E402


def has_cjk(value: str) -> bool:
    return any("\u4e00" <= char <= "\u9fff" for char in value)


def source_strings(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    values: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and has_cjk(node.value):
            values.add(node.value)
    return values


def main() -> int:
    gui = ROOT / "gui_app.py"
    values = source_strings(gui)
    untranslated = sorted(value for value in values if has_cjk(i18n.tr(value)))
    if untranslated:
        print(f"{len(untranslated)} GUI strings still contain Chinese after translation:")
        for value in untranslated:
            print(repr(value))
        return 1
    print(f"Validated {len(values)} Chinese GUI literals: all render in English")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
