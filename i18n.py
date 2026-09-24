"""Runtime English localization for the upstream Chinese GUI."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_CATALOG = Path(__file__).resolve().parent / "locales" / "en.json"
_translations: dict[str, str] = {}


def _load() -> None:
    global _translations
    try:
        with _CATALOG.open(encoding="utf-8") as handle:
            data = json.load(handle)
        _translations = {str(k): str(v) for k, v in data.items() if v}
    except (OSError, json.JSONDecodeError):
        _translations = {}


def tr(value: Any) -> Any:
    """Translate a UI value while preserving non-string values."""
    if not isinstance(value, str):
        return value
    translated = _translations.get(value, value)
    if translated != value:
        return translated
    for source, target in sorted(_translations.items(), key=lambda item: len(item[0]), reverse=True):
        if source in value:
            value = value.replace(source, target)
    return value


def _translate_kwargs(kwargs: dict[str, Any]) -> dict[str, Any]:
    for key in ("text", "placeholder_text", "title", "message"):
        if key in kwargs:
            kwargs[key] = tr(kwargs[key])
    return kwargs


def install() -> None:
    """Patch CustomTkinter widgets and Tk dialogs at the shared GUI boundary."""
    _load()
    import customtkinter as ctk
    from tkinter import messagebox

    for class_name in ("CTkLabel", "CTkButton", "CTkCheckBox", "CTkRadioButton", "CTkEntry"):
        cls = getattr(ctk, class_name, None)
        if cls is None or getattr(cls, "_english_localized", False):
            continue
        original_init = cls.__init__

        def localized_init(self, *args, _original=original_init, **kwargs):
            _original(self, *args, **_translate_kwargs(kwargs))

        cls.__init__ = localized_init
        original_configure = cls.configure

        def localized_configure(self, *args, _original=original_configure, **kwargs):
            _original(self, *args, **_translate_kwargs(kwargs))

        cls.configure = localized_configure
        cls._english_localized = True

    for name in ("showerror", "showwarning", "showinfo", "askyesno"):
        original = getattr(messagebox, name)
        if getattr(original, "_english_localized", False):
            continue

        def localized_dialog(title, message, *args, _original=original, **kwargs):
            return _original(tr(title), tr(message), *args, **kwargs)

        localized_dialog._english_localized = True
        setattr(messagebox, name, localized_dialog)


_load()
