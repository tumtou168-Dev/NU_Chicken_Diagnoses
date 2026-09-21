# app/services/page_text_service.py
from typing import List, Optional

from flask import g, has_request_context
from markupsafe import Markup, escape

from extensions import db
from app.i18n import ordered
from app.models import PermissionTable, RoleTable
from app.models.page_text import PageText

# key -> (page, where it is used, Khmer, English). Rows are inserted into the database
# when missing; after that the database is the source of truth and admins edit it there.
DEFAULTS = {
    "diagnose.title": ("diagnose", "Browser tab title", "ធ្វើរោគវិនិច្ឆ័យ", "Diagnose"),
    "diagnose.heading": ("diagnose", "Page heading", "ការធ្វើរោគវិនិច្ឆ័យថ្មី", "New diagnosis"),
    "diagnose.subheading": ("diagnose", "Text under the page heading",
                            "ជ្រើសរើសរោគសញ្ញាដែលបានសង្កេតឃើញដើម្បីកំណត់អត្តសញ្ញាណជំងឺដែលអាចកើតមាន។",
                            "Select the symptoms you observed to identify possible diseases."),
    "diagnose.observations.title": ("diagnose", "Symptom card title", "ការសង្កេត", "Observations"),
    "diagnose.observations.subtitle": ("diagnose", "Symptom card subtitle",
                                       "តើអ្នកឃើញរោគសញ្ញាអ្វីខ្លះ?", "Which symptoms do you see?"),
    "diagnose.search.placeholder": ("diagnose", "Symptom search box placeholder",
                                    "ស្វែងរករោគសញ្ញា...", "Search symptoms..."),
    "diagnose.search.label": ("diagnose", "Symptom search box accessible label",
                              "ស្វែងរករោគសញ្ញា", "Search symptoms"),
    "diagnose.search.empty": ("diagnose", "Shown when the symptom search matches nothing",
                              "រកមិនឃើញរោគសញ្ញាដែលត្រូវគ្នាទេ", "No matching symptoms"),
    "diagnose.clear": ("diagnose", "Clear-selection button", "សម្អាតការជ្រើសរើស", "Clear selection"),
    "diagnose.selected": ("diagnose", "Selected-symptoms counter. Use %(n)s for the number.",
                          "បានជ្រើស %(n)s", "%(n)s selected"),
    "diagnose.submit": ("diagnose", "Analyse button", "វិភាគរោគសញ្ញា", "Analyse symptoms"),
    "diagnose.results.title": ("diagnose", "Results heading", "លទ្ធផលនៃការវិភាគ", "Analysis results"),
    "diagnose.results.found": ("diagnose", "Results count badge. Use %(n)s for the number.",
                               "រកឃើញ %(n)s", "%(n)s found"),
    "diagnose.result.confidence": ("diagnose", "Label under the confidence percentage",
                                   "ទំនុកចិត្ត", "Confidence"),
    "diagnose.result.description": ("diagnose", "Disease description label", "ការពិពណ៌នា", "Description"),
    "diagnose.result.treatment": ("diagnose", "Disease treatment label", "ការព្យាបាល", "Treatment"),
    "diagnose.result.rule": ("diagnose", "Matched-rule footer. Use %(rule)s and %(n)s.",
                             "វិធានដែលត្រូវគ្នា៖ %(rule)s (%(n)s រោគសញ្ញាត្រូវគ្នា)",
                             "Matched rule: %(rule)s (%(n)s matching symptoms)"),
    "diagnose.nomatch.title": ("diagnose", "Title when no disease matches", "រកមិនឃើញការផ្គូផ្គងទេ", "No match found"),
    "diagnose.nomatch.body": ("diagnose", "Text when no disease matches",
                              "យើងមិនអាចរកឃើញជំងឺដែលត្រូវនឹងបន្សំនៃរោគសញ្ញានេះទេ។ សូមព្យាយាមជ្រើសរើសរោគសញ្ញាផ្សេង ឬតិចជាងនេះ។",
                              "We could not find a disease matching this combination of symptoms. Try selecting different or fewer symptoms."),
    "diagnose.empty.title": ("diagnose", "Title before a diagnosis is run",
                             "ត្រៀមខ្លួនធ្វើរោគវិនិច្ឆ័យ", "Ready to diagnose"),
    "diagnose.empty.body": ("diagnose", "Text before a diagnosis is run",
                            "ជ្រើសរើសរោគសញ្ញាដែលអ្នកសង្កេតឃើញពីបញ្ជីខាងក្រោម។ ប្រព័ន្ធជំនាញរបស់យើងនឹងវិភាគពួកវា និងណែនាំជំងឺ និងការព្យាបាលដែលអាចកើតមាន។",
                            "Select the symptoms you observe from the list below. Our expert system will analyse them and suggest possible diseases and treatments."),
    "diagnose.empty.point1": ("diagnose", "First check-mark line", "ការវិភាគរហ័ស", "Fast analysis"),
    "diagnose.empty.point2": ("diagnose", "Second check-mark line", "វិធានអ្នកជំនាញ", "Expert rules"),
}

# Khmer version of each row's "where it is used" note (DEFAULTS holds the English one).
DESCRIPTIONS_KM = {
    "diagnose.title": "ចំណងជើងផ្ទាំងកម្មវិធីរុករក",
    "diagnose.heading": "ចំណងជើងទំព័រ",
    "diagnose.subheading": "អត្ថបទនៅក្រោមចំណងជើងទំព័រ",
    "diagnose.observations.title": "ចំណងជើងកាតរោគសញ្ញា",
    "diagnose.observations.subtitle": "ចំណងជើងរងនៃកាតរោគសញ្ញា",
    "diagnose.search.placeholder": "អត្ថបទគំរូក្នុងប្រអប់ស្វែងរករោគសញ្ញា",
    "diagnose.search.label": "ស្លាកសម្រាប់ភាពងាយស្រួលនៃប្រអប់ស្វែងរករោគសញ្ញា",
    "diagnose.search.empty": "បង្ហាញនៅពេលការស្វែងរករោគសញ្ញារកមិនឃើញអ្វីទាំងអស់",
    "diagnose.clear": "ប៊ូតុងសម្អាតការជ្រើសរើស",
    "diagnose.selected": "ទ្រនិចរាប់រោគសញ្ញាដែលបានជ្រើស។ ប្រើ %(n)s សម្រាប់ចំនួន។",
    "diagnose.submit": "ប៊ូតុងវិភាគ",
    "diagnose.results.title": "ចំណងជើងលទ្ធផល",
    "diagnose.results.found": "ស្លាកចំនួនលទ្ធផល។ ប្រើ %(n)s សម្រាប់ចំនួន។",
    "diagnose.result.confidence": "ស្លាកក្រោមភាគរយទំនុកចិត្ត",
    "diagnose.result.description": "ស្លាកការពិពណ៌នាជំងឺ",
    "diagnose.result.treatment": "ស្លាកការព្យាបាលជំងឺ",
    "diagnose.result.rule": "បាតកថាវិធានដែលត្រូវគ្នា។ ប្រើ %(rule)s និង %(n)s។",
    "diagnose.nomatch.title": "ចំណងជើងនៅពេលរកមិនឃើញជំងឺដែលត្រូវគ្នា",
    "diagnose.nomatch.body": "អត្ថបទនៅពេលរកមិនឃើញជំងឺដែលត្រូវគ្នា",
    "diagnose.empty.title": "ចំណងជើងមុនពេលធ្វើរោគវិនិច្ឆ័យ",
    "diagnose.empty.body": "អត្ថបទមុនពេលធ្វើរោគវិនិច្ឆ័យ",
    "diagnose.empty.point1": "ចំណុចធីកទីមួយ",
    "diagnose.empty.point2": "ចំណុចធីកទីពីរ",
}

# Earlier default wording, replaced on start only while an admin has not edited it.
LEGACY = {
    "diagnose.empty.body": ('ជ្រើសរើសរោគសញ្ញាដែលអ្នកសង្កេតឃើញពីបញ្ជីនៅខាងឆ្វេង។ ប្រព័ន្ធជំនាញរបស់យើងនឹងវិភាគពួកវា និងណែនាំជំងឺ និងការព្យាបាលដែលអាចកើតមាន។', 'Select the symptoms you observe from the list on the left. Our expert system will analyse them and suggest possible diseases and treatments.'),
}

PERMISSION = ("manage_page_texts", "Manage Page Texts", "Expert System")


class PageTextService:
    @staticmethod
    def ensure_defaults() -> None:
        """Insert any missing default rows and the permission that guards the editor (never overwrites)."""
        existing = {k for (k,) in db.session.execute(db.select(PageText.key))}
        for key, (page, description, km, en) in DEFAULTS.items():
            if key not in existing:
                db.session.add(PageText(key=key, page=page, description=description,
                                        description_km=DESCRIPTIONS_KM.get(key), text_km=km, text_en=en))

        for row in db.session.scalars(db.select(PageText).filter(PageText.description_km.is_(None))):
            row.description_km = DESCRIPTIONS_KM.get(row.key)

        for key, (old_km, old_en) in LEGACY.items():
            row = db.session.scalar(db.select(PageText).filter_by(key=key))
            if row is not None and row.text_km == old_km and (row.text_en or None) == old_en:
                row.text_km, row.text_en = DEFAULTS[key][2], DEFAULTS[key][3]

        code, name, module = PERMISSION
        perm = db.session.scalar(db.select(PermissionTable).filter_by(code=code))
        if perm is None:
            perm = PermissionTable(code=code, name=name, module=module)
            db.session.add(perm)
            admin = db.session.scalar(db.select(RoleTable).filter_by(name="Admin"))
            if admin is not None:
                admin.permissions.append(perm)
        db.session.commit()

    @staticmethod
    def get_all() -> List[PageText]:
        return PageText.query.order_by(PageText.page.asc(), PageText.id.asc()).all()

    @staticmethod
    def get_by_id(text_id: int) -> Optional[PageText]:
        return db.session.get(PageText, text_id)

    @staticmethod
    def update(item: PageText, km: str, en: Optional[str]) -> PageText:
        item.text_km = km.strip()
        item.text_en = (en or "").strip() or None
        db.session.commit()
        return item

    @staticmethod
    def reset(item: PageText) -> PageText:
        default = DEFAULTS.get(item.key)
        if default:
            item.text_km, item.text_en = default[2], default[3]
            db.session.commit()
        return item

    # ---- rendering -------------------------------------------------------
    @staticmethod
    def _cache() -> dict:
        if not has_request_context():
            return {}
        if not hasattr(g, "_page_texts"):
            g._page_texts = {k: (km, en) for k, km, en in
                             db.session.execute(db.select(PageText.key, PageText.text_km, PageText.text_en))}
        return g._page_texts

    @classmethod
    def _pair(cls, key: str):
        """(first, second) for `key`, current language first. Falls back to the built-in default, then the key."""
        km, en = cls._cache().get(key) or (None, None)
        if km is None and key in DEFAULTS:
            km, en = DEFAULTS[key][2], DEFAULTS[key][3]
        first, second = ordered(km or "", en or "")
        return (first or key), second

    @staticmethod
    def _fill(value: str, params: dict) -> Markup:
        """Escape the stored text, then substitute the (escaped) params."""
        safe = Markup(escape(value))
        if not params:
            return safe
        try:
            return safe % params
        except (KeyError, ValueError, TypeError):
            return safe  # an admin typo in a placeholder must not break the page

    @classmethod
    def text(cls, key: str, **params) -> Markup:
        """Text for `key` in BOTH languages on one line ("first · second"), current language first.
        The stored text and every param are HTML-escaped (pass Markup for params that carry markup)."""
        first, second = cls._pair(key)
        first = cls._fill(first, params)
        return first if not second else Markup("%s · %s") % (first, cls._fill(second, params))

    @classmethod
    def block(cls, key: str, **params) -> Markup:
        """Same, as two lines (current language large, the other smaller underneath) for headings and buttons."""
        first, second = cls._pair(key)
        first = cls._fill(first, params)
        if not second:
            return first
        return Markup('<span class="dual"><span class="dual-1">%s</span><span class="dual-2">%s</span></span>') % (
            first, cls._fill(second, params))
