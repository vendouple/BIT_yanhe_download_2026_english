"""Fail when a user-visible GUI literal still renders with Chinese text."""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

for stream_name in ("stdout", "stderr"):
    stream = getattr(sys, stream_name, None)
    if stream is not None:
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError):
            pass

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


def output_strings(path: Path) -> set[str]:
    """Collect literal fragments passed to print/log/progress output calls."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    values: set[str] = set()
    for call in (node for node in ast.walk(tree) if isinstance(node, ast.Call)):
        is_print = isinstance(call.func, ast.Name) and call.func.id == "print"
        is_log = (
            isinstance(call.func, ast.Attribute)
            and call.func.attr in {"debug", "info", "warning", "error", "exception"}
        )
        if not (is_print or is_log):
            continue
        for node in ast.walk(call):
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and has_cjk(node.value):
                values.add(node.value)
    return values


def backend_strings() -> set[str]:
    backend_files = {
        "batch_process.py",
        "audio_transcriber_gpu.py",
        "ppt_extractor_gpu.py",
        "m3u8dl.py",
        "utils.py",
        "fetch_ffmpeg.py",
    }
    return set().union(
        *(output_strings(ROOT / name) for name in sorted(backend_files))
    )


def main() -> int:
    gui = ROOT / "gui_app.py"
    values = source_strings(gui)
    gui_catalog_path = ROOT / "locales" / "en_gui.json"
    gui_catalog = json.loads(gui_catalog_path.read_text(encoding="utf-8"))
    untranslated = sorted(
        value for value in values
        if gui_catalog.get(value) and has_cjk(i18n.tr(value))
    )
    missing = sorted(value for value in values if not gui_catalog.get(value))
    if untranslated:
        print(f"{len(untranslated)} GUI strings still contain Chinese after translation:")
        for value in untranslated:
            print(repr(value))
        return 1
    print(f"Validated {len(values)} Chinese GUI literals: all render in English")
    if missing:
        print(
            f"Warning: {len(missing)} GUI strings have no English translation yet; "
            "Chinese fallback is retained"
        )

    output_values = backend_strings()
    backend_catalog = json.loads(
        (ROOT / "locales" / "en_backend.json").read_text(encoding="utf-8")
    )
    untranslated_output = sorted(
        value
        for value in output_values
        if backend_catalog.get(value) and has_cjk(i18n.tr(value))
    )
    missing_output = sorted(value for value in output_values if not backend_catalog.get(value))
    if untranslated_output:
        print(f"Error: {len(untranslated_output)} log/console fragments still contain Chinese")
        for value in untranslated_output:
            print(repr(value))
        return 1
    print(f"Validated {len(output_values)} log/console fragments: all render in English")
    if missing_output:
        print(
            f"Warning: {len(missing_output)} backend strings have no English translation yet; "
            "Chinese fallback is retained"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
