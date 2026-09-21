# app/forms/expert_system_forms.py
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField, IntegerField, FloatField, SelectField
from app.forms import validation as val
from app.i18n import lazy, gettext as _
from app.forms.multi_checkbox_field import MultiCheckboxField
from app.models.expert_system import Category, Disease, Symptom, Rule
from extensions import db


def _label(item) -> str:
    """Both names for selects and checkbox lists, current language first."""
    return item.inline("name")


def _category_choices():
    items = db.session.scalars(
        db.select(Category).order_by(Category.name)
    ).all()
    return [(0, lazy("គ្មានប្រភេទ"))] + [(c.id, _label(c)) for c in items]


def _disease_choices():
    items = db.session.scalars(
        db.select(Disease).order_by(Disease.name)
    ).all()
    return [(d.id, _label(d)) for d in items]


def _symptom_choices():
    items = db.session.scalars(
        db.select(Symptom).order_by(Symptom.name)
    ).all()
    return [(s.id, _label(s)) for s in items]


class CategoryForm(FlaskForm):
    name = StringField(lazy("ឈ្មោះ (អង់គ្លេស)"), validators=[val.required(), val.length(min=2, max=120)])
    name_km = StringField(lazy("ឈ្មោះ (ខ្មែរ)"), validators=[val.length(max=120)])
    description = TextAreaField(lazy("ការពិពណ៌នា (អង់គ្លេស)"))
    description_km = TextAreaField(lazy("ការពិពណ៌នា (ខ្មែរ)"), validators=[val.length(max=255)])
    submit = SubmitField(lazy("រក្សាទុក"))


class SymptomForm(FlaskForm):
    name = StringField(lazy("ឈ្មោះរោគសញ្ញា (អង់គ្លេស)"), validators=[val.required(), val.length(min=2, max=120)])
    name_km = StringField(lazy("ឈ្មោះរោគសញ្ញា (ខ្មែរ)"), validators=[val.length(max=120)])
    description = TextAreaField(lazy("ការពិពណ៌នា (អង់គ្លេស)"))
    description_km = TextAreaField(lazy("ការពិពណ៌នា (ខ្មែរ)"), validators=[val.length(max=255)])
    submit = SubmitField(lazy("រក្សាទុក"))


class DiseaseForm(FlaskForm):
    name = StringField(lazy("ឈ្មោះជំងឺ (អង់គ្លេស)"), validators=[val.required(), val.length(min=2, max=120)])
    name_km = StringField(lazy("ឈ្មោះជំងឺ (ខ្មែរ)"), validators=[val.length(max=120)])
    description = TextAreaField(lazy("ការពិពណ៌នា (អង់គ្លេស)"), validators=[val.required(), val.length(min=5, max=255)])
    description_km = TextAreaField(lazy("ការពិពណ៌នា (ខ្មែរ)"), validators=[val.length(max=255)])
    treatment = TextAreaField(lazy("ការព្យាបាលដែលបានណែនាំ (អង់គ្លេស)"), validators=[val.required(), val.length(min=5, max=255)])
    treatment_km = TextAreaField(lazy("ការព្យាបាលដែលបានណែនាំ (ខ្មែរ)"), validators=[val.length(max=255)])
    category_id = SelectField(lazy("ប្រភេទ##one"), coerce=int)
    submit = SubmitField(lazy("រក្សាទុក"))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.category_id.choices = _category_choices()


class RuleForm(FlaskForm):
    title = StringField(lazy("ចំណងជើងវិធាន (អង់គ្លេស)"), validators=[val.required(), val.length(min=2, max=120)])
    title_km = StringField(lazy("ចំណងជើងវិធាន (ខ្មែរ)"), validators=[val.length(max=120)])
    description = TextAreaField(lazy("ការពិពណ៌នាវិធាន (អង់គ្លេស)"), validators=[val.required(), val.length(min=5, max=255)])
    description_km = TextAreaField(lazy("ការពិពណ៌នាវិធាន (ខ្មែរ)"), validators=[val.length(max=255)])
    priority = IntegerField(lazy("អាទិភាព"), validators=[val.required(), val.number_range(min=1, max=100)])
    confidence = FloatField(lazy("ទំនុកចិត្តមូលដ្ឋាន (%)"), validators=[val.required(), val.number_range(min=1, max=100)])
    disease_id = SelectField(lazy("ជំងឺ##one"), coerce=int, validators=[val.required()])
    symptom_ids = MultiCheckboxField(lazy("រោគសញ្ញា"), coerce=int)
    submit = SubmitField(lazy("រក្សាទុក"))

    def __init__(self, original_rule: Rule | None = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.disease_id.choices = _disease_choices()
        self.symptom_ids.choices = _symptom_choices()
        if original_rule and not self.is_submitted():
            self.symptom_ids.data = [s.id for s in original_rule.symptoms]


class PageTextForm(FlaskForm):
    text_km = TextAreaField(lazy("អត្ថបទជាភាសាខ្មែរ"), validators=[val.required(), val.length(max=2000)])
    text_en = TextAreaField(lazy("អត្ថបទជាភាសាអង់គ្លេស"), validators=[val.length(max=2000)])
    submit = SubmitField(lazy("រក្សាទុក"))
