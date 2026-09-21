# app/models/bilingual.py
"""Khmer/English content for the knowledge-base models. Both languages are shown together; the language toggle
decides which comes first.

The original column (e.g. ``name``) holds the English text; an optional ``<column>_km``
sibling holds the Khmer text. Missing Khmer text never renders blank: the English is shown alone.
"""
from markupsafe import Markup

from app.i18n import ordered, pair_text


def bilingual(km: str | None, en: str | None) -> Markup:
    """Two lines: current language first, the other one smaller underneath. A single line when only one exists."""
    first, second = ordered((km or "").strip(), (en or "").strip())
    if not second:
        return Markup("%s") % first
    return Markup('<span class="dual"><span class="dual-1">%s</span><span class="dual-2">%s</span></span>') % (first, second)


class BilingualMixin:
    def loc(self, field: str) -> str:
        """One language only (the current one, falling back to the other) - for places that need plain text."""
        first, _second = ordered((getattr(self, f"{field}_km") or "").strip(), (getattr(self, field) or "").strip())
        return first or ""

    def pair(self, field: str) -> Markup:
        """Both languages on two lines (see bilingual())."""
        return bilingual(getattr(self, f"{field}_km"), getattr(self, field))

    def inline(self, field: str) -> str:
        """Both languages on one line ("first · second"), for badges and tags."""
        first, second = ordered((getattr(self, f"{field}_km") or "").strip(), (getattr(self, field) or "").strip())
        return pair_text(first, second)
