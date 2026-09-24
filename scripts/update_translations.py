"""Keep the English catalog aligned with Chinese literals in the GUI."""

from __future__ import annotations

import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_FILES = [ROOT / "gui_app.py", ROOT / "app_paths.py"]
CATALOG = ROOT / "locales" / "en.json"


def strings_from_python(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and any("\u4e00" <= char <= "\u9fff" for char in node.value)
    }


def main() -> None:
    catalog = json.loads(CATALOG.read_text(encoding="utf-8")) if CATALOG.exists() else {}
    discovered = set().union(*(strings_from_python(path) for path in SOURCE_FILES if path.exists()))
    missing = sorted(source for source in discovered if source not in catalog)
    for source in missing:
        catalog[source] = ""
    if missing:
        CATALOG.write_text(json.dumps(dict(sorted(catalog.items())), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Discovered {len(discovered)} strings; added {len(missing)} new entries")


if __name__ == "__main__":
    main()
