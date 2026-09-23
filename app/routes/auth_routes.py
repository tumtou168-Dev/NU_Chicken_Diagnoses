import re
import secrets
import time
import urllib.parse
import requests
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, session
from flask_login import login_user, logout_user, login_required, current_user
from extensions import db
from app.i18n import gettext as _
from app.models.user import UserTable
from app.models.role import RoleTable
from app.services.user_service import UserService
from app.services.audit_service import AuditService
from app.services.email_service import EmailService, generate_reset_token, verify_reset_token

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


def _signup_errors(username: str, email: str, full_name: str, password: str, confirm_password: str) -> list[str]:
    """Checks shared by the normal sign-up form and the "complete your Google account" form."""
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
    return errors


def _default_role_id() -> int | None:
    role = RoleTable.query.filter_by(name="User").first()
    return role.id if role else None


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        full_name = request.form.get("full_name", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        errors = _signup_errors(username, email, full_name, password, confirm_password)
        if errors:
            for msg in errors:
                flash(msg, "danger")
            return render_template(
                "auth/register.html",
                username=username,
                email=email,
                full_name=full_name,
            )
            
        new_user = UserService.create_user(
            data={
                "username": username,
                "email": email,
                "full_name": full_name,
                "is_active": True,
            },
            password=password,
            role_id=_default_role_id(),
        )
        
        login_user(new_user)
        AuditService.log("REGISTER", "User", new_user.id, "New user registered")
        flash(_("បានបង្កើតគណនីដោយជោគជ័យ។ អ្នកបានចូលរួចហើយ។"), "success")

        return redirect(url_for(new_user.landing_endpoint()))
    
    return render_template("auth/register.html")


@auth_bp.route("/google")
def google_login():
    client_id = current_app.config.get("GOOGLE_CLIENT_ID")
    if not client_id:
        flash(_("ការចូលតាម Google មិនទាន់ត្រូវបានកំណត់រចនាសម្ព័ន្ធទេ។ សូមទាក់ទងអ្នកគ្រប់គ្រង។"), "warning")
        return redirect(request.referrer or url_for("auth.login"))

    state = secrets.token_urlsafe(32)
    session["oauth_state"] = state

    redirect_uri = url_for("auth.google_callback", _external=True)
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "offline",
        "prompt": "select_account",
    }
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"
    return redirect(auth_url)


@auth_bp.route("/google/callback")
def google_callback():
    client_id = current_app.config.get("GOOGLE_CLIENT_ID")
    client_secret = current_app.config.get("GOOGLE_CLIENT_SECRET")

    if not client_id or not client_secret:
        flash(_("ការចូលតាម Google មិនទាន់ត្រូវបានកំណត់រចនាសម្ព័ន្ធទេ។"), "danger")
        return redirect(url_for("auth.login"))

    state = request.args.get("state")
    saved_state = session.pop("oauth_state", None)
    if not state or state != saved_state:
        flash(_("សុពលភាពសុវត្ថិភាពបរាជ័យ (State mismatch)។ សូមព្យាយាមម្តងទៀត។"), "danger")
        return redirect(url_for("auth.login"))

    code = request.args.get("code")
    if not code:
        err = request.args.get("error", "Access denied")
        flash(_("ការចូលតាម Google ត្រូវបានបោះបង់ ឬបរាជ័យ៖ %(error)s", error=err), "warning")
        return redirect(url_for("auth.login"))

    # Exchange code for tokens
    redirect_uri = url_for("auth.google_callback", _external=True)
    token_url = "https://oauth2.googleapis.com/token"
    token_data = {
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }

    try:
        token_resp = requests.post(token_url, data=token_data, timeout=10)
        token_json = token_resp.json()
        if token_resp.status_code != 200 or "access_token" not in token_json:
            flash(_("មិនអាចទាញយកព័ត៌មានផ្ទៀងផ្ទាត់ពី Google បានទេ។"), "danger")
            return redirect(url_for("auth.login"))

        access_token = token_json["access_token"]

        # Fetch user profile info
        userinfo_resp = requests.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10,
        )
        userinfo = userinfo_resp.json()
        if userinfo_resp.status_code != 200 or "email" not in userinfo:
            flash(_("មិនអាចទទួលព័ត៌មានគណនីពី Google បានទេ។"), "danger")
            return redirect(url_for("auth.login"))

    except Exception:
        flash(_("មានបញ្ហាក្នុងការតភ្ជាប់ជាមួយសេវាកម្ម Google។"), "danger")
        return redirect(url_for("auth.login"))

    email = userinfo.get("email", "").strip().lower()

    user = UserTable.query.filter_by(email=email).first()

    if user:
        if not user.is_active:
            flash(_("គណនីរបស់អ្នកអសកម្ម។ សូមទាក់ទងអ្នកគ្រប់គ្រង។"), "warning")
            return redirect(url_for("auth.login"))

        login_user(user)
        AuditService.log("LOGIN", "User", user.id, f"Google login: {user.username}")
        flash(_("បានចូលតាមរយៈ Google ដោយជោគជ័យ។"), "success")
        return redirect(url_for(user.landing_endpoint()))

    # New Google user: nothing is created yet. Keep the verified e-mail for a few minutes and ask
    # them to fill in their account (username, name, password) before they get into the system.
    session[GOOGLE_SIGNUP_KEY] = {"email": email, "expires": time.time() + GOOGLE_SIGNUP_TTL}
    return redirect(url_for("auth.google_complete"))


GOOGLE_SIGNUP_KEY = "google_signup"
GOOGLE_SIGNUP_TTL = 15 * 60   # seconds to finish the "complete your account" form


def _pending_google_signup() -> dict | None:
    pending = session.get(GOOGLE_SIGNUP_KEY)
    if not pending or pending.get("expires", 0) < time.time():
        session.pop(GOOGLE_SIGNUP_KEY, None)
        return None
    return pending


@auth_bp.route("/google/complete", methods=["GET", "POST"])
def google_complete():
    """Step 2 of signing up with Google: the visitor fills in their details; only then is the
    account created and are they signed in."""
    if current_user.is_authenticated:
        return redirect(url_for(current_user.landing_endpoint()))
    pending = _pending_google_signup()
    if pending is None:
        flash(_("ការចុះឈ្មោះតាម Google បានផុតកំណត់។ សូមព្យាយាមម្តងទៀត។"), "warning")
        return redirect(url_for("auth.register"))

    email = pending["email"]
    username = full_name = ""   # the visitor types these; nothing is pre-filled from Google

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        full_name = request.form.get("full_name", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        errors = _signup_errors(username, email, full_name, password, confirm_password)
        if not errors:
            new_user = UserService.create_user(
                data={"username": username, "email": email, "full_name": full_name, "is_active": True},
                password=password,
                role_id=_default_role_id(),
            )
            session.pop(GOOGLE_SIGNUP_KEY, None)
            login_user(new_user)
            AuditService.log("REGISTER", "User", new_user.id, f"Google registration: {new_user.username}")
            flash(_("បានចុះឈ្មោះ និងចូលតាមរយៈ Google ដោយជោគជ័យ។"), "success")
            return redirect(url_for(new_user.landing_endpoint()))
        for msg in errors:
            flash(msg, "danger")

    return render_template("auth/google_complete.html", email=email, username=username, full_name=full_name)


@auth_bp.route("/google/cancel", methods=["POST"])
def google_cancel():
    """Drop a half-finished Google sign-up."""
    session.pop(GOOGLE_SIGNUP_KEY, None)
    flash(_("បានបោះបង់ការចុះឈ្មោះតាម Google។"), "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/logout")
@login_required
def logout():
    user_id = current_user.id
    # Drop the chat "online" dot right away (updated_at pinned — logging out isn't a profile edit).
    db.session.execute(
        db.update(UserTable).where(UserTable.id == user_id).values(last_seen_at=None, updated_at=UserTable.updated_at)
    )
    db.session.commit()
    logout_user()
    AuditService.log("LOGOUT", "User", user_id, "User logged out")
    flash(_("អ្នកបានចាកចេញរួចរាល់។"), "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        if not email:
            flash(_("សូមបញ្ចូលអាសយដ្ឋានអ៊ីមែលរបស់អ្នក។"), "danger")
            return render_template("auth/forgot_password.html", email=email)

        user = UserTable.query.filter_by(email=email).first()
        if user and user.is_active:
            token = generate_reset_token(user.email, current_app.config["SECRET_KEY"])
            reset_url = url_for("auth.reset_password", token=token, _external=True)
            EmailService.send_password_reset_email(user.email, reset_url, user.full_name)
            AuditService.log("PASSWORD_RESET_REQUEST", "User", user.id, f"Password reset requested for {user.username}")

        # Always show the same message to protect against email enumeration attacks
        flash(_("ប្រសិនបើអ៊ីមែលនេះមានក្នុងប្រព័ន្ធ យើងបានផ្ញើតំណភ្ជាប់ដើម្បីកំណត់ពាក្យសម្ងាត់ឡើងវិញទៅកាន់អ៊ីមែលរបស់អ្នកហើយ។"), "info")
        return redirect(url_for("auth.login"))

    return render_template("auth/forgot_password.html")


@auth_bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token: str):
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    email = verify_reset_token(token, current_app.config["SECRET_KEY"], max_age=3600)
    if not email:
        flash(_("តំណភ្ជាប់កំណត់ពាក្យសម្ងាត់ឡើងវិញមិនត្រឹមត្រូវ ឬផុតកំណត់ហើយ។ សូមស្នើសុំម្តងទៀត។"), "danger")
        return redirect(url_for("auth.forgot_password"))

    user = UserTable.query.filter_by(email=email).first()
    if not user:
        flash(_("រកមិនឃើញគណនីរបស់អ្នកប្រើប្រាស់នេះទេ។"), "danger")
        return redirect(url_for("auth.forgot_password"))

    if request.method == "POST":
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        errors: list[str] = []
        if not password:
            errors.append(_("សូមបញ្ចូលពាក្យសម្ងាត់ថ្មី។"))
        elif len(password) < 8:
            errors.append(_("ពាក្យសម្ងាត់ត្រូវមានយ៉ាងតិច ៨ តួអក្សរ។"))
        elif not re.search(r"[A-Z]", password):
            errors.append(_("ពាក្យសម្ងាត់ត្រូវមានអក្សរធំ (A-Z) យ៉ាងតិចមួយ។"))
        elif not re.search(r"[a-z]", password):
            errors.append(_("ពាក្យសម្ងាត់ត្រូវមានអក្សរតូច (a-z) យ៉ាងតិចមួយ។"))
        elif not re.search(r"[0-9]", password):
            errors.append(_("ពាក្យសម្ងាត់ត្រូវមានលេខ (0-9) យ៉ាងតិចមួយ។"))
        elif not re.search(r"[!@#$%^&*()<>?\"{}|<>_\-+=]", password):
            errors.append(_("ពាក្យសម្ងាត់ត្រូវមាននិមិត្តសញ្ញាពិសេសយ៉ាងតិចមួយ (ឧ. ! @ # $)។"))

        if password and password != confirm_password:
            errors.append(_("ពាក្យសម្ងាត់មិនដូចគ្នាទេ។"))

        if errors:
            for msg in errors:
                flash(msg, "danger")
            return render_template("auth/reset_password.html", token=token, email=email)

        user.set_password(password)
        db.session.commit()
        AuditService.log("PASSWORD_RESET", "User", user.id, f"Password reset successful for {user.username}")
        flash(_("ពាក្យសម្ងាត់របស់អ្នកត្រូវបានកំណត់ឡើងវិញដោយជោគជ័យ។ សូមចូលប្រើប្រាស់។"), "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/reset_password.html", token=token, email=email)


