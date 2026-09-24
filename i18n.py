"""Runtime English localization for the upstream Chinese GUI."""

from __future__ import annotations

import json
import logging
import re
import sys
from pathlib import Path
from typing import Any

from app_paths import resource_path

_CATALOG = Path(resource_path("locales/en.json"))
_translations: dict[str, str] = {}
_MISSING_MEDIA_PATTERN = re.compile(r"在 (?P<path>.+) 中未找到媒体文件")
_DURATION_PATTERN = re.compile(
    r"(?P<prefix>音频时长: |视频时长: |开始转录 \(|Audio duration: |"
    r"Video duration: |Starting transcription \()"
    r"(?P<minutes>\d+)分(?P<seconds>\d+)秒"
)
_STATUS_UNIT_PATTERN = re.compile(
    r"(?P<prefix>成功\(|Success\()(?P<count>\d+)(?P<unit>张|段)(?P<suffix>\))"
)


def _load() -> None:
    global _translations
    catalogs = [_CATALOG]
    if _CATALOG.parent.is_dir():
        catalogs.extend(sorted(_CATALOG.parent.glob("en_*.json")))
        catalogs.extend(sorted(_CATALOG.parent.glob("*_en.json")))
    merged: dict[str, str] = {}
    for catalog in catalogs:
        try:
            with catalog.open(encoding="utf-8") as handle:
                data = json.load(handle)
            merged.update({str(k): str(v) for k, v in data.items() if v})
        except (OSError, json.JSONDecodeError, TypeError):
            continue
    _translations = merged


def tr(value: Any) -> Any:
    """Translate a UI value while preserving non-string values."""
    if not isinstance(value, str):
        return value
    translated = _translations.get(value, value)
    if translated != value:
        return translated
    missing_media = _MISSING_MEDIA_PATTERN.fullmatch(value)
    if missing_media:
        return f"No media files found in {missing_media.group('path')}"
    value = _DURATION_PATTERN.sub(
        lambda match: (
            f"{match.group('prefix')}{match.group('minutes')} min "
            f"{match.group('seconds')} sec"
        ),
        value,
    )
    value = _STATUS_UNIT_PATTERN.sub(
        lambda match: (
            f"{match.group('prefix')}{match.group('count')} "
            f"{'slides' if match.group('unit') == '张' else 'segments'}{match.group('suffix')}"
        ),
        value,
    )
    for source, target in sorted(_translations.items(), key=lambda item: len(item[0]), reverse=True):
        # Short fragments such as "网络" or "课程" can occur in server error
        # text and should not corrupt otherwise useful exception details.
        if len(source.strip()) < 4 and source.strip() == source and all(char.isalnum() for char in source):
            continue
        if source in value:
            value = value.replace(source, target)
    return value


def _translate_kwargs(kwargs: dict[str, Any]) -> dict[str, Any]:
    for key in ("text", "placeholder_text", "title", "message"):
        if key in kwargs:
            kwargs[key] = tr(kwargs[key])
    if "values" in kwargs and isinstance(kwargs["values"], (list, tuple)):
        kwargs["values"] = type(kwargs["values"])(tr(value) for value in kwargs["values"])
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


def _install_console_translation() -> None:
    _install_logging_translation()
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream is not None and not getattr(stream, "_i18n_translated_stream", False):
            setattr(sys, stream_name, _TranslatedStream(stream))


def install_console() -> None:
    """Translate console output and logging without importing GUI dependencies."""
    _load()
    _install_console_translation()


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
    install_console()
    import customtkinter as ctk
    from tkinter import filedialog, messagebox

    for class_name in (
        "CTkLabel", "CTkButton", "CTkCheckBox", "CTkRadioButton", "CTkEntry",
        "CTkOptionMenu", "CTkComboBox", "CTkSegmentedButton",
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

    for class_name in ("CTk", "CTkToplevel"):
        cls = getattr(ctk, class_name, None)
        if cls is None or getattr(cls, "_english_title_localized", False):
            continue
        original_title = cls.title

        def localized_title(self, *args, _original=original_title, **kwargs):
            if args:
                args = (tr(args[0]),) + args[1:]
            return _original(self, *args, **kwargs)

        cls.title = localized_title
        cls._english_title_localized = True

    for name in (
        "showerror", "showwarning", "showinfo", "askquestion", "askokcancel",
        "askretrycancel", "askyesno", "askyesnocancel",
    ):
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
