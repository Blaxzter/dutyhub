"""Notification message translations loaded from JSON locale files."""

import json
from pathlib import Path
from typing import Any

DEFAULT_LANGUAGE = "en"

_LOCALES_DIR = Path(__file__).parent / "locales"

# Load all locale JSON files at import time
_messages: dict[str, dict[str, Any]] = {}
for locale_file in _LOCALES_DIR.glob("*.json"):
    lang = locale_file.stem
    with open(locale_file, encoding="utf-8") as f:
        _messages[lang] = json.load(f)


def _resolve_lang(language: str) -> str:
    """Return the language code if supported, otherwise fall back to default."""
    return language if language in _messages else DEFAULT_LANGUAGE


def get_message(type_code: str, language: str, **kwargs: str) -> tuple[str, str]:
    """Return (title, body) for a notification type in the given language.

    Falls back to English if the language is not found.
    kwargs are passed to str.format() on the body template.
    """
    lang = _resolve_lang(language)
    msg = _messages.get(lang, _messages[DEFAULT_LANGUAGE]).get(type_code)
    if not msg:
        # Graceful fallback: try English, then return raw type_code
        msg = _messages[DEFAULT_LANGUAGE].get(
            type_code, {"title": type_code, "body": ""}
        )

    title = msg["title"]
    body = msg["body"].format(**kwargs) if kwargs else msg["body"]
    return title, body


def get_email_strings(language: str) -> dict[str, str]:
    """Return email template strings for the given language."""
    lang = _resolve_lang(language)
    return _messages.get(lang, _messages[DEFAULT_LANGUAGE]).get(
        "email", _messages[DEFAULT_LANGUAGE]["email"]
    )
