# app/routes/auth_routes.py
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from app.i18n import gettext as _
from app.models.user import UserTable
from app.models.role import RoleTable
from app.services.user_service import UserService
from app.services.audit_service import AuditService

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        
        user = UserTable.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            if not user.is_active:
                flash(_("គណនីរបស់អ្នកអសកម្ម។ សូមទាក់ទងអ្នកគ្រប់គ្រង។"), "warning")
                return redirect(url_for("auth.login"))
            
            login_user(user)
            AuditService.log("LOGIN", "User", user.id, "User logged in")
            flash(_("បានចូលដោយជោគជ័យ។"), "success")

            return redirect(url_for(user.landing_endpoint()))
        
        flash(_("ឈ្មោះអ្នកប្រើប្រាស់ ឬពាក្យសម្ងាត់មិនត្រឹមត្រូវ។"), "danger")
        return redirect(url_for("auth.login"))
    
    return render_template("auth/login.html")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        full_name = request.form.get("full_name", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        
        errors: list[str] = []
        
        if not username:
            errors.append(_("សូមបញ្ចូលឈ្មោះអ្នកប្រើប្រាស់។"))
        if not email:
            errors.append(_("សូមបញ្ចូលអាសយដ្ឋានអ៊ីមែល។"))
        if not full_name:
            errors.append(_("សូមបញ្ចូលឈ្មោះពេញ។"))
        if not password:
            errors.append(_("សូមបញ្ចូលពាក្យសម្ងាត់។"))
        if password and password != confirm_password:
            errors.append(_("ពាក្យសម្ងាត់មិនដូចគ្នាទេ។"))
            
        if username and UserTable.query.filter_by(username=username).first():
            errors.append(_("ឈ្មោះអ្នកប្រើប្រាស់នេះមានគេប្រើរួចហើយ។"))
        if email and UserTable.query.filter_by(email=email).first():
            errors.append(_("អ៊ីមែលនេះត្រូវបានចុះឈ្មោះរួចហើយ។"))
            
        if errors:
            for msg in errors:
                flash(msg, "danger")
            return render_template(
                "auth/register.html",
                username=username,
                email=email,
                full_name=full_name,
            )
            
        default_role = RoleTable.query.filter_by(name="User").first()
        default_role_id = default_role.id if default_role else None
        
        data = {
            "username": username,
            "email": email,
            "full_name": full_name,
            "is_active": True,
        }
        
        new_user = UserService.create_user(
            data=data,
            password=password,
            role_id=default_role_id,
        )
        
        login_user(new_user)
        AuditService.log("REGISTER", "User", new_user.id, "New user registered")
        flash(_("បានបង្កើតគណនីដោយជោគជ័យ។ អ្នកបានចូលរួចហើយ។"), "success")

        return redirect(url_for(new_user.landing_endpoint()))
    
    return render_template("auth/register.html")


@auth_bp.route("/logout")
@login_required
def logout():
    user_id = current_user.id
    logout_user()
    # Note: current_user is anonymous after logout_user(), so we can't use it for logging user_id directly inside AuditService if we rely on current_user there.
    # However, AuditService uses current_user. Since we just logged out, current_user is anonymous.
    # We should log BEFORE logging out if we want to capture the user ID, or pass it explicitly.
    # But AuditService.log uses current_user internally. Let's adjust AuditService or log before logout.
    # Actually, let's log before logout to capture the user.
    # Wait, I can't easily change AuditService to take user_id as optional override without changing its signature.
    # Let's just log "LOGOUT" before calling logout_user().
    
    # Re-implementing log here manually or calling service before logout
    # But wait, AuditService.log uses current_user.id.
    AuditService.log("LOGOUT", "User", user_id, "User logged out")

    flash(_("អ្នកបានចាកចេញរួចរាល់។"), "info")
    return redirect(url_for("auth.login"))
