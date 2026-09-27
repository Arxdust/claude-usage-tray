"""UI translations — strings live in locales/<code>.json, picked via the tray menu.

Usage: t("menu.refresh") or t("common.resets", reset="in 2h 14m").
A key missing from the current language falls back to English, then to the
`default` argument, then to the key itself.
"""
from __future__ import annotations

import json
import os
from typing import Any

# language code -> name in that language (shown in the tray menu)
LANGUAGES = {
    "en": "English",
    "uk": "Українська",
    "ru": "Русский",
    "th": "ไทย",
}
DEFAULT = "th"
FALLBACK = "en"

_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "locales")
_tables: dict[str, dict[str, str]] = {}
_lang = DEFAULT


def _table(code: str) -> dict[str, str]:
    if code not in _tables:
        try:
            with open(os.path.join(_DIR, f"{code}.json"), encoding="utf-8") as f:
                _tables[code] = json.load(f)
        except (OSError, ValueError):
            _tables[code] = {}  # missing/broken file -> fall back to English
    return _tables[code]


def set_language(code: str | None) -> str:
    """Switch the UI language; unknown codes fall back to DEFAULT. Returns the code in use."""
    global _lang
    _lang = code if code in LANGUAGES else DEFAULT
    return _lang


def get_language() -> str:
    return _lang


def t(key: str, default: str | None = None, **kwargs: Any) -> str:
    text = _table(_lang).get(key) or _table(FALLBACK).get(key) or default or key
    return text.format(**kwargs) if kwargs else text
