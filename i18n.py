"""Runtime English localization for the upstream Chinese GUI."""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any

from app_paths import resource_path

_CATALOG = Path(resource_path("locales/en.json"))
_translations: dict[str, str] = {}


def _load() -> None:
    global _translations
    catalogs = [_CATALOG]
    if _CATALOG.parent.is_dir():
        catalogs.extend(sorted(_CATALOG.parent.glob("en_*.json")))
        catalogs.extend(sorted(_CATALOG.parent.glob("*_en.json")))
    merged: dict[str, str] = {}
    try:
        for catalog in catalogs:
            with catalog.open(encoding="utf-8") as handle:
                data = json.load(handle)
            merged.update({str(k): str(v) for k, v in data.items() if v})
        _translations = merged
    except (OSError, json.JSONDecodeError, TypeError):
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


class _TranslatedStream:
    """Translate human-readable console output without changing data files."""

    _i18n_translated_stream = True

    def __init__(self, stream):
        self._stream = stream

    def write(self, value):
        return self._stream.write(tr(value) if isinstance(value, str) else value)

    def __getattr__(self, name):
        return getattr(self._stream, name)


def _install_logging_translation() -> None:
    factory = logging.getLogRecordFactory()
    if getattr(factory, "_i18n_translated_factory", False):
        return

    def translated_factory(*args, **kwargs):
        record = factory(*args, **kwargs)
        try:
            # Format first so f-strings and %-style logger calls are both covered.
            record.msg = tr(record.getMessage())
            record.args = ()
        except Exception:
            pass
        return record

    translated_factory._i18n_translated_factory = True
    logging.setLogRecordFactory(translated_factory)


def install() -> None:
    """Patch CustomTkinter widgets and Tk dialogs at the shared GUI boundary."""
    _load()
    import customtkinter as ctk
    from tkinter import filedialog, messagebox

    _install_logging_translation()
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream is not None and not getattr(stream, "_i18n_translated_stream", False):
            setattr(sys, stream_name, _TranslatedStream(stream))

    for class_name in (
        "CTkLabel", "CTkButton", "CTkCheckBox", "CTkRadioButton", "CTkEntry",
        "CTkOptionMenu", "CTkComboBox",
    ):
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

    textbox = getattr(ctk, "CTkTextbox", None)
    if textbox is not None and not getattr(textbox, "_english_localized", False):
        original_insert = textbox.insert

        def localized_insert(self, index, text, *args, _original=original_insert, **kwargs):
            return _original(self, index, tr(text), *args, **kwargs)

        textbox.insert = localized_insert
        textbox._english_localized = True

    for name in ("showerror", "showwarning", "showinfo", "askyesno"):
        original = getattr(messagebox, name)
        if getattr(original, "_english_localized", False):
            continue

        def localized_dialog(title, message, *args, _original=original, **kwargs):
            return _original(tr(title), tr(message), *args, **kwargs)

        localized_dialog._english_localized = True
        setattr(messagebox, name, localized_dialog)

    for name in ("askdirectory", "askopenfilename", "asksaveasfilename"):
        original = getattr(filedialog, name)
        if getattr(original, "_english_localized", False):
            continue

        def localized_file_dialog(*args, _original=original, **kwargs):
            if "title" in kwargs:
                kwargs["title"] = tr(kwargs["title"])
            return _original(*args, **kwargs)

        localized_file_dialog._english_localized = True
        setattr(filedialog, name, localized_file_dialog)


_load()
