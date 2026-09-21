# app/i18n.py
"""Minimal Khmer/English translation layer (no external dependency).

Khmer is the source language: the Khmer text itself is the lookup key, and
app/translations/en.py maps it to English. By default only the language chosen with the toggle is shown; with
config SHOW_BOTH_LANGUAGES every string is shown in BOTH languages ("Khmer · English"), chosen language first. A key missing from the catalogue shows the Khmer text alone,
so a string can never render blank.
"""
from flask import current_app, has_request_context, request
from markupsafe import Markup, escape

from app.translations.en import EN
from app.translations.data_km import DATA_KM
from app.translations import audit_km

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


SEP = " · "


def split_pair(text: str):
    """(khmer, english_or_None) for a translation key, with any context marker removed."""
    km = text.partition(CONTEXT_MARK)[0]
    en = EN.get(text)
    en = en.partition(CONTEXT_MARK)[0] if en else None
    return km, (en if en and en != km else None)


def both_languages() -> bool:
    """True when the app is configured to show Khmer and English together (config SHOW_BOTH_LANGUAGES)."""
    try:
        return bool(current_app.config.get("SHOW_BOTH_LANGUAGES", False))
    except RuntimeError:  # no app context
        return False


def ordered(km, en):
    """(first, second) for the current language.

    Single-language mode: second is always None - only the current language is shown, falling back to the other
    one when it has no text. Both-languages mode: second is the other language."""
    if not en:
        return km, None
    if not km:
        return en, None
    first, second = (en, km) if get_locale() == "en" else (km, en)
    return (first, second) if both_languages() else (first, None)


def gettext(text: str, **params) -> str:
    """Both languages on one line, current language first. Use %(name)s placeholders with keyword params."""
    first, second = ordered(*split_pair(text))
    if params:
        first = first % params
        second = second % params if second else None
    return first if second is None else f"{first}{SEP}{second}"


def gettext_html(text: str, **params) -> Markup:
    """Like gettext, but returns Markup and HTML-escapes every inserted value (Markup values pass through)."""
    first, second = ordered(*split_pair(text))
    first = Markup(first) % params if params else Markup(first)
    if second is None:
        return first
    second = Markup(second) % params if params else Markup(second)
    return Markup("%s%s%s") % (first, SEP, second)


def gettext_pair(text: str, **params) -> Markup:
    """Two-line label markup (current language large, the other one small underneath) for headings, buttons and
    the sidebar. Template helper `bi()`. Params are HTML-escaped."""
    first, second = ordered(*split_pair(text))
    if params:
        first = first % params
        second = second % params if second else None
    if second is None:
        return Markup("<span>%s</span>") % first
    return Markup('<span class="dual"><span class="dual-1">%s</span><span class="dual-2">%s</span></span>') % (first, second)


def gettext_inline(text: str, **params) -> str:
    """Plain one-line version for HTML attributes and JS-swapped labels (template helper `bit()`)."""
    return gettext(text, **params)


def pair_text(first, second):
    """Join two texts as "first · second" (either may be empty)."""
    return f"{first}{SEP}{second}" if first and second and first != second else (first or second or "")


def data_text(value):
    """Built-in role/permission name or description in both languages, current language first."""
    if not value:
        return value
    km = DATA_KM.get(value)
    return value if not km else pair_text(*ordered(km, value))


def audit_target(value):
    km = audit_km.TARGETS.get(value) if value else None
    return value if not km else pair_text(*ordered(km, value))


def audit_action(value):
    km = audit_km.ACTIONS.get(value) if value else None
    return value if not km else pair_text(*ordered(km, value.capitalize()))


def audit_detail(value):
    """Audit-log message (stored in English) with its Khmer translation."""
    km = audit_km.detail_km(value) if value else None
    return value if not km or km == value else pair_text(*ordered(km, value))


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
