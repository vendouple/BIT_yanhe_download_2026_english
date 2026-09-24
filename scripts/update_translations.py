"""Keep the English catalog aligned with Chinese literals in the GUI."""

from __future__ import annotations

import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_FILES = sorted(
    path for path in ROOT.glob("*.py")
    if path.name not in {"i18n.py", "theme.py"}
)
CATALOG = ROOT / "locales" / "en.json"
GUI_CATALOG = ROOT / "locales" / "en_gui.json"
BACKEND_CATALOGS = (
    ROOT / "locales" / "backend_en.json",
    ROOT / "locales" / "en_backend.json",
)


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

    gui_catalog = json.loads(GUI_CATALOG.read_text(encoding="utf-8")) if GUI_CATALOG.exists() else {}
    gui_strings = strings_from_python(ROOT / "gui_app.py")
    missing_gui = sorted(source for source in gui_strings if source not in gui_catalog)
    for source in missing_gui:
        gui_catalog[source] = ""
    if missing_gui:
        GUI_CATALOG.write_text(
            json.dumps(dict(sorted(gui_catalog.items())), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    backend_catalog_path = next((path for path in BACKEND_CATALOGS if path.exists()), None)
    if backend_catalog_path is not None:
        backend_catalog = json.loads(backend_catalog_path.read_text(encoding="utf-8"))
        backend_strings = set().union(
            *(strings_from_python(path) for path in SOURCE_FILES if path.name != "gui_app.py")
        )
        missing_backend = sorted(source for source in backend_strings if source not in backend_catalog)
        for source in missing_backend:
            backend_catalog[source] = ""
        if missing_backend:
            backend_catalog_path.write_text(
                json.dumps(dict(sorted(backend_catalog.items())), ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
    else:
        missing_backend = []
    print(
        f"Discovered {len(discovered)} strings; added {len(missing)} general and "
        f"{len(missing_gui)} GUI and {len(missing_backend)} backend entries"
    )


if __name__ == "__main__":
    main()
