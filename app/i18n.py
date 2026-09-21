# app/i18n.py
"""Minimal Khmer/English translation layer (no external dependency).

Khmer is the source language: the Khmer text itself is the lookup key, and
app/translations/en.py maps it to English. A key missing from the catalogue falls
back to the Khmer text, so a string can never render blank.
"""
from flask import has_request_context, request
from markupsafe import Markup, escape

from app.translations.en import EN
from app.translations.data_km import DATA_KM

LANGUAGES = {"km": "ខ្មែរ", "en": "English"}
DEFAULT_LANGUAGE = "km"
COOKIE_NAME = "lang"
CONTEXT_MARK = "##"   # "តួនាទី##one": same Khmer text, separate English entry; the marker never shows


def get_locale() -> str:
    if has_request_context():
        lang = request.cookies.get(COOKIE_NAME)
        if lang in LANGUAGES:
            return lang
    return DEFAULT_LANGUAGE


def _lookup(text: str) -> str:
    """English text when available, otherwise the Khmer source (with any context marker removed)."""
    if get_locale() == "en":
        found = EN.get(text)
        if found is not None:
            return found
    return text.partition(CONTEXT_MARK)[0]


def gettext_pair(text: str, **params) -> Markup:
    """Label markup for the current language only (Khmer mode is all Khmer, English mode all English).

    Kept as the template helper `bi()`. Accepts %(name)s params (HTML-escaped)."""
    return Markup(escape(gettext(text, **params)))


def gettext_inline(text: str, **params) -> str:
    """Plain-text version of gettext_pair for attributes and JS-swapped labels (template helper `bit()`)."""
    return gettext(text, **params)


def data_text(value):
    """Display text for a built-in role/permission name or description: Khmer in Khmer mode, as stored otherwise."""
    if value and get_locale() == "km":
        return DATA_KM.get(value, value)
    return value


def gettext(text: str, **params) -> str:
    """Translate `text` for the current request. Use %(name)s placeholders with keyword params."""
    text = _lookup(text)
    return text % params if params else text


def gettext_html(text: str, **params) -> Markup:
    """Like gettext, but returns Markup and HTML-escapes every inserted value (Markup values pass through)."""
    text = _lookup(text)
    return Markup(text) % params if params else Markup(text)


class LazyString:
    """A string translated when it is rendered, for labels and messages defined at import time."""

    def __init__(self, text: str, **params):
        self._text = text
        self._params = params

    def __str__(self) -> str:
        return gettext(self._text, **self._params)

    def __html__(self) -> str:
        return str(escape(str(self)))

    def __repr__(self) -> str:
        return f"LazyString({self._text!r})"

    def __mod__(self, _other) -> str:
        # WTForms validators apply `message % {...}`; our text is already fully formatted.
        return str(self)

    def __add__(self, other):
        return str(self) + str(other)

    def __radd__(self, other):
        return str(other) + str(self)

    def __eq__(self, other):
        return str(self) == str(other)

    def __hash__(self):
        return hash(self._text)

    def __len__(self):
        return len(str(self))

    def __bool__(self):
        return bool(self._text)


def lazy(text: str, **params) -> LazyString:
    return LazyString(text, **params)


def safe_next_url(target, fallback: str = "/") -> str:
    """Only allow same-site relative paths, so the language switch cannot be used as an open redirect."""
    if not target or not target.startswith("/") or target.startswith("//") or "\\" in target:
        return fallback
    return target
