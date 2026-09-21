# app/models/bilingual.py
"""Khmer/English content for the knowledge-base models. The language toggle picks which one is shown.

The original column (e.g. ``name``) holds the English text; an optional ``<column>_km``
sibling holds the Khmer text. Missing Khmer text never renders blank: it falls back to English.
"""
from markupsafe import Markup

from app.i18n import get_locale


def bilingual(km: str | None, en: str | None) -> Markup:
    """The text in the current language, falling back to the other one when it is empty."""
    km, en = (km or "").strip(), (en or "").strip()
    return Markup("%s") % ((en or km) if get_locale() == "en" else (km or en))


class BilingualMixin:
    def loc(self, field: str) -> str:
        """The value in the current language, falling back to the other one."""
        en, km = getattr(self, field) or "", getattr(self, f"{field}_km") or ""
        return (en or km) if get_locale() == "en" else (km or en)

    def pair(self, field: str) -> Markup:
        """The text in the current language (see bilingual())."""
        return bilingual(getattr(self, f"{field}_km"), getattr(self, field))

    def inline(self, field: str) -> str:
        """Same as loc(); kept for badges and tags."""
        return self.loc(field)
