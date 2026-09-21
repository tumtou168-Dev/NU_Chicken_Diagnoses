# app/forms/role_forms.py
from collections import defaultdict
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField
from wtforms.validators import ValidationError
from app.forms import validation as val
from app.i18n import lazy, gettext as _
from app.models import RoleTable, PermissionTable
from extensions import db
from app.i18n import data_text
from app.forms.multi_checkbox_field import MultiCheckboxField

def _permission_choices():
    """Flat (id, label) list, used for field binding only."""
    return [
        (perm.id, f"{perm.code} - {data_text(perm.name)}")
        for perm in db.session.scalars(
            db.select(PermissionTable).order_by(PermissionTable.code)
        ).all()
    ]
    
def _permissions_grouped_by_module():
    """
    Return permissions grouped by module:
    {
        "users": [Permission, ...],
        "Roles": [Permission, ...],
        ...
    }
    """
    perms = db.session.scalars(
        db.select(PermissionTable).order_by(
            PermissionTable.module, PermissionTable.code
        )
    ).all()
    grouped = defaultdict(list)
    for perm in perms:
        module = perm.module or "General"
        grouped[module].append(perm)
    return dict(grouped)

class RoleCreateForm(FlaskForm):
    name = StringField(
        lazy("ឈ្មោះ"),
        validators=[val.required(), val.length(min=2, max=80)],
        render_kw={"placeholder": lazy("ឈ្មោះតួនាទី")},
    )
    description = TextAreaField(
        lazy("ការពិពណ៌នា"),
        render_kw={"placeholder": lazy("ការពិពណ៌នាសង្ខេប (មិនបង្ខំ)")},
    )
    
    permission_ids = MultiCheckboxField(
        lazy("សិទ្ធិ"),
        coerce=int,
        render_kw={"placeholder": lazy("សិទ្ធិដែលផ្តល់ឱ្យតួនាទីនេះ")},
    )
    
    submit = SubmitField(lazy("រក្សាទុក"))
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.permission_ids.choices = _permission_choices()
        self.permissions_by_module = _permissions_grouped_by_module()
        
    def validate_name(self, field):
        exists = db.session.scalar(
            db.select(RoleTable).filter(RoleTable.name == field.data)
        )
        if exists:
            raise ValidationError(_("ឈ្មោះតួនាទីនេះមានរួចហើយ។"))
        

class RoleEditForm(FlaskForm):
    name = StringField(
        lazy("ឈ្មោះ"),
        validators=[val.required(), val.length(min=2, max=80)],
    )
    description = TextAreaField(lazy("ការពិពណ៌នា"))
    
    permission_ids = MultiCheckboxField(lazy("សិទ្ធិ"),
        coerce=int,
    )
    
    submit = SubmitField(lazy("រក្សាទុកការផ្លាស់ប្តូរ"))
    
    def __init__(self, original_role: RoleTable,*args, **kwargs):
        super().__init__(*args, **kwargs)
        self.original_role = original_role
        self.permission_ids.choices = _permission_choices()
        self.permission_by_module = _permissions_grouped_by_module()
        
        if not self.is_submitted():
            self.permission_ids.data = [p.id for p in original_role.permissions]
            
    def validate_name(self, field):
        q = db.select(RoleTable).filter(
            RoleTable.name == field.data,
            RoleTable.id != self.original_role.id,
        )
        exists = db.session.scalar(q)
        if exists:
            raise ValidationError(_("ឈ្មោះតួនាទីនេះមានរួចហើយ។"))

class RoleConfirmDeleteForm(FlaskForm):
    submit = SubmitField(lazy("បញ្ជាក់ការលុប"))
