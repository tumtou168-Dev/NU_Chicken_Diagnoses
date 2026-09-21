# app/forms/permission_forms.py
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField, SelectField
from wtforms.validators import ValidationError
from app.forms import validation as val
from app.i18n import lazy, gettext as _
from app.models.permission import PermissionTable
from extensions import db

# (stored value, Khmer label). Values stay English because they are stored in the database.
MODULE_CHOICES = [
    ("Users", lazy("អ្នកប្រើប្រាស់")),
    ("Roles", lazy("តួនាទី")),
    ("Permissions", lazy("សិទ្ធិ")),
    ("Expert System", lazy("ប្រព័ន្ធជំនាញ")),
    ("Facts", lazy("ទិន្នន័យ")),
    ("System", lazy("ប្រព័ន្ធ")),
    ("Audit", lazy("សវនកម្ម")),
    ("General", lazy("ទូទៅ")),
]
MODULE_LABELS = dict(MODULE_CHOICES)

class PermissionCreateForm(FlaskForm):
    code = StringField(
        lazy("កូដ"),
        validators=[val.required(), val.length(min=2, max=64)],
        render_kw={"placeholder": lazy("ឧ. user.view")},
    )
    name = StringField(
        lazy("ឈ្មោះ"),
        validators=[val.required(), val.length(min=2, max=120)],
        render_kw={"placeholder": lazy("ឈ្មោះដែលអាចអានបាន")},
    )
    module = SelectField(
        lazy("ម៉ូឌុល"),
        choices=MODULE_CHOICES,
        default="General",
    )
    description = TextAreaField(
        lazy("ការពិពណ៌នា"),
        render_kw={"placeholder": lazy("តើសិទ្ធិនេះអនុញ្ញាតឱ្យធ្វើអ្វី?")},
    )
    
    submit = SubmitField(lazy("រក្សាទុក"))
    
    def validate_code(self, field):
        exists = db.session.scalar(
            db.select(PermissionTable).filter(PermissionTable.code == field.data)
        )
        if exists:
            raise ValidationError(_("កូដសិទ្ធិនេះត្រូវបានប្រើរួចហើយ។"))
        
    def validate_name(self, field):
        exists = db.session.scalar(
            db.select(PermissionTable).filter(PermissionTable.name == field.data)
        )
        if exists:
            raise ValidationError(_("ឈ្មោះសិទ្ធិនេះត្រូវបានប្រើរួចហើយ។"))
        
class PermissionEditForm(FlaskForm):
    code = StringField(
        lazy("កូដ"),
        validators=[val.required(), val.length(min=2, max=64)],
    )
    name = StringField(
        lazy("ឈ្មោះ"),
        validators=[val.required(), val.length(min=2, max=120)],
    )
    module = SelectField(
        lazy("ម៉ូឌុល"),
        choices=MODULE_CHOICES,
        default="General",
    )
    description = TextAreaField(lazy("ការពិពណ៌នា"))
    
    submit = SubmitField(lazy("រក្សាទុកការផ្លាស់ប្តូរ"))
    
    def __init__(self, original_permission: PermissionTable, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.original_permission = original_permission
        if not self.is_submitted():
            self.module.data = original_permission.module
            
    def validate_code(self, field):
        q = db.select(PermissionTable).filter(
            PermissionTable.code == field.data,
            PermissionTable.id != self.original_permission.id,
        )
        exists = db.session.scalar(q)
        if exists:
            raise ValidationError(_("កូដសិទ្ធិនេះត្រូវបានប្រើរួចហើយ។"))
    
    def validate_name(self, field):
        q = db.select(PermissionTable).filter(
            PermissionTable.name == field.data,
            PermissionTable.id != self.original_permission.id,
        )
        exists = db.session.scalar(q)
        if exists:
            raise ValidationError(_("ឈ្មោះសិទ្ធិនេះត្រូវបានប្រើរួចហើយ។"))
        
class PermissionConfirmDeleteForm(FlaskForm):
    submit = SubmitField(lazy("បញ្ជាក់ការលុប"))