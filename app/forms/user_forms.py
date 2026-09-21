# app/forms/user_forms.py
import re
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import ( BooleanField, StringField, SubmitField, PasswordField, SelectField)
from wtforms.validators import ValidationError, Optional
from app.forms import validation as val
from app.i18n import lazy, gettext as _, data_text
from app.models.user import UserTable
from app.models.role import RoleTable
from extensions import db
from app.services.avatar_service import AvatarService, ALLOWED_EXTENSIONS

# --------- helprt validators ---------
def strong_password(form, field):
    """Require: min 8 chars, upper, lower, digit, special."""
    password = field.data or ""
    if len(password) < 8:
        raise ValidationError(_("ពាក្យសម្ងាត់ត្រូវមានយ៉ាងតិច ៨ តួអក្សរ។"))
    if not re.search(r"[A-Z]", password):
        raise ValidationError(_("ពាក្យសម្ងាត់ត្រូវមានអក្សរធំ (A-Z) យ៉ាងតិចមួយ។"))
    if not re.search(r"[a-z]",password):
        raise ValidationError(_("ពាក្យសម្ងាត់ត្រូវមានអក្សរតូច (a-z) យ៉ាងតិចមួយ។"))
    if not re.search(r"[0-9]", password):
        raise ValidationError(_("ពាក្យសម្ងាត់ត្រូវមានលេខ (0-9) យ៉ាងតិចមួយ។"))
    if not re.search(r"[!@#$%^&*()<>?\"{}|<>_\-+=]", password):
        raise ValidationError(_("ពាក្យសម្ងាត់ត្រូវមាននិមិត្តសញ្ញាពិសេសយ៉ាងតិចមួយ (ឧ. ! @ # $)។"))
    
def _role_choices():
    """Return list of (id, name) tuples for all roles. orderd by name."""
    return [
        (role.id, data_text(role.name))
        for role in db.session.scalars(
            db.select(RoleTable).order_by(RoleTable.name)
        )
    ]
    
# ------------------------ create from ------------------------
class UserCreateForm(FlaskForm):
    username = StringField(
        lazy("ឈ្មោះអ្នកប្រើប្រាស់"),
        validators=[val.required(), val.length(min=3, max=80)],
        render_kw={"placeholder": lazy("បញ្ចូលឈ្មោះអ្នកប្រើប្រាស់")},
    )
    email = StringField(
        lazy("អាសយដ្ឋានអ៊ីមែល"),
        validators=[val.required(), val.email(), val.length(max=120)],
        render_kw={"placeholder": lazy("បញ្ចូលអាសយដ្ឋានអ៊ីមែល")},
    )
    full_name = StringField(
        lazy("ឈ្មោះពេញ"),
        validators=[val.required(), val.length(min=3, max=120)],
        render_kw={"placeholder": lazy("បញ្ចូលឈ្មោះពេញ")},
    )
    is_active = BooleanField(lazy("គណនីសកម្ម"), default=True)
    
    role_id = SelectField(
        lazy("តួនាទី##one"),
        coerce=int,
        validators=[val.required()],
        render_kw={"placeholder": lazy("ជ្រើសរើសតួនាទី")},
    )
    
    password = PasswordField(
        lazy("ពាក្យសម្ងាត់"),
        validators=[val.required(), strong_password],
        render_kw={"placeholder": lazy("ពាក្យសម្ងាត់រឹងមាំ")},
    )
    confirm_password = PasswordField(
        "Confirm_password",
        validators=[
            val.required(),
            val.passwords_match(),
        ],
        render_kw={"placeholder": lazy("បញ្ជាក់ពាក្យសម្ងាត់")}
    )
    
    submit = SubmitField(lazy("រក្សាទុក"))
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.role_id.choices = _role_choices()
        
        # Default to the least-privileged role so an admin never creates an Admin by accident.
        if not self.is_submitted():
            self.role_id.data = next((rid for rid, name in self.role_id.choices if name == data_text("User")), None)
        
    def validate_username(self, field):
        exists = db.session.scalar(
            db.select(UserTable).filter(UserTable.username == field.data)
        )
        if exists:
            raise ValidationError(_("ឈ្មោះអ្នកប្រើប្រាស់នេះមានគេប្រើរួចហើយ។"))
        
    def validate_email(self, field):
        exists = db.session.scalar(
            db.select(UserTable).filter(UserTable.email == field.data)
        )
        if exists:
            raise ValidationError(_("អ៊ីមែលនេះត្រូវបានចុះឈ្មោះរួចហើយ។"))
        
# ---------------- edit form ----------------
class UserEditForm(FlaskForm):
    username = StringField(
        lazy("ឈ្មោះអ្នកប្រើប្រាស់"),
        validators=[val.required(), val.length(min=3, max=80)],
    )
    email = StringField(
        lazy("អាសយដ្ឋានអ៊ីមែល"),
        validators=[val.required(), val.email(), val.length(max=120)],
    )
    full_name = StringField(
        lazy("ឈ្មោះពេញ"),
        validators=[val.required(), val.length(min=3, max=120)],
    )
    is_active = BooleanField(lazy("គណនីសកម្ម"))
    
    avatar = FileField(
        lazy("រូបភាពប្រវត្តិរូប"),
        validators=[FileAllowed(list(ALLOWED_EXTENSIONS), lazy("អនុញ្ញាតតែរូបភាព JPG, PNG ឬ WebP ប៉ុណ្ណោះ។"))],
        render_kw={"accept": "image/jpeg,image/png,image/webp"},
    )
    remove_avatar = BooleanField(lazy("លុបរូបភាពបច្ចុប្បន្ន"))
    
    role_id = SelectField(
        lazy("តួនាទី##one"),
        coerce=int,
        validators=[val.required()],
    )
    
    password = PasswordField(
        lazy("ពាក្យសម្ងាត់ថ្មី"),
        validators=[Optional(), strong_password],
        render_kw={"placeholder": lazy("ពាក្យសម្ងាត់ថ្មីដ៏រឹងមាំ (មិនបង្ខំ)")},
    )
    confirm_password = PasswordField(
        lazy("បញ្ជាក់ពាក្យសម្ងាត់ថ្មី"),
        validators=[val.passwords_match()],
    )
    
    submit = SubmitField(lazy("រក្សាទុកការផ្លាស់ប្តូរ"))
    
    def __init__(self, original_user: UserTable, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.original_user = original_user
        self.role_id.choices = _role_choices()
        
        if not self.is_submitted():
            if original_user.roles:
                self.role_id.data = original_user.roles[0].id
            else:
                self.role_id.data = None
                
    def validate_avatar(self, field):
        if field.data and getattr(field.data, "filename", ""):
            error = AvatarService.validate(field.data)
            if error:
                raise ValidationError(error)
                
    def validate_username(self, field):
        q = db.select(UserTable).filter(
            UserTable.username == field.data,
            UserTable.id != self.original_user.id,
        )
        exists = db.session.scalar(q)
        if exists:
            raise ValidationError(_("ឈ្មោះអ្នកប្រើប្រាស់នេះមានគេប្រើរួចហើយ។"))
        
    def validate_email(self, field):
        q = db.select(UserTable).filter(
            UserTable.email == field.data,
            UserTable.id != self.original_user.id,
        )
        exists = db.session.scalar(q)
        if exists:
            raise ValidationError(_("អ៊ីមែលនេះត្រូវបានចុះឈ្មោះរួចហើយ។"))
        
# ----------- confirm delete form -----------
class UserConfirmDeleteForm(FlaskForm):
    submit = SubmitField(lazy("បញ្ជាក់ការលុប"))
    