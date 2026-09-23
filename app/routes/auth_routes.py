import re
import secrets
import time
import urllib.parse
import requests
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, session, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from extensions import db
from app.i18n import gettext as _
from app.models.user import UserTable
from app.models.role import RoleTable
from app.services.user_service import UserService
from app.services.audit_service import AuditService
from app.models.password_reset import PasswordResetCode
from app.services.password_reset_service import PasswordResetService

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        
        # Accept email too: Google sign-ups get a generated username they may not know
        user = UserTable.query.filter_by(username=username).first() or _find_user_by_email(username)
        
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
    full_name = userinfo.get("name", "").strip() or email.split("@")[0]

    user = _find_user_by_email(email)

    if user:
        if not user.is_active:
            flash(_("គណនីរបស់អ្នកអសកម្ម។ សូមទាក់ទងអ្នកគ្រប់គ្រង។"), "warning")
            return redirect(url_for("auth.login"))

        login_user(user)
        AuditService.log("LOGIN", "User", user.id, f"Google login: {user.username}")
        flash(_("បានចូលតាមរយៈ Google ដោយជោគជ័យ។"), "success")
        if not user.password_set:
            return redirect(url_for("auth.set_password"))
        return redirect(url_for(user.landing_endpoint()))

    # Register new user from Google account
    default_role = RoleTable.query.filter_by(name="User").first()
    default_role_id = default_role.id if default_role else None

    # Generate clean unique username
    base_user = re.sub(r"[^a-zA-Z0-9_]", "", (userinfo.get("given_name") or email.split("@")[0]).lower())
    if not base_user or len(base_user) < 3:
        base_user = re.sub(r"[^a-zA-Z0-9_]", "", email.split("@")[0].lower())
    if not base_user or len(base_user) < 3:
        base_user = "user"

    candidate_username = base_user[:70]
    count = 1
    while UserTable.query.filter_by(username=candidate_username).first():
        candidate_username = f"{base_user[:65]}_{count}"
        count += 1

    random_pw = secrets.token_urlsafe(24) + "A1!"

    new_user = UserService.create_user(
        data={
            "username": candidate_username,
            "email": email,
            "full_name": full_name,
            "is_active": True,
        },
        password=random_pw,
        role_id=default_role_id,
    )

    new_user.password_set = False  # the random password above is never shown to anyone
    db.session.commit()

    login_user(new_user)
    AuditService.log("REGISTER", "User", new_user.id, f"Google registration: {new_user.username}")
    flash(_("បានចុះឈ្មោះ និងចូលតាមរយៈ Google ដោយជោគជ័យ។"), "success")
    return redirect(url_for("auth.set_password"))


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
    flash(_("អ្នកបានចាកចេញរួចរាល់។"), "success")
    return redirect(url_for("auth.login"))


def _find_user_by_email(email: str) -> UserTable | None:
    # Emails are stored as typed at registration, so compare case-insensitively.
    return UserTable.query.filter(db.func.lower(UserTable.email) == email.strip().lower()).first()


def _new_password_errors(password: str, confirm_password: str) -> list[str]:
    """Same strength rules as the admin user form (forms/user_forms.strong_password)."""
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
    return errors


USERNAME_RE = re.compile(r"^[A-Za-z0-9_.]{3,80}$")


def _username_errors(username: str, user: UserTable) -> list[str]:
    if not USERNAME_RE.match(username):
        return [_("ឈ្មោះអ្នកប្រើប្រាស់ត្រូវមាន ៣-៨០ តួ ហើយប្រើបានតែអក្សរ លេខ _ និង . ប៉ុណ្ណោះ។")]
    taken = UserTable.query.filter(
        db.func.lower(UserTable.username) == username.lower(), UserTable.id != user.id
    ).first()
    if taken:
        return [_("ឈ្មោះអ្នកប្រើប្រាស់នេះមានគេប្រើរួចហើយ។")]
    return []


@auth_bp.before_app_request
def require_password_setup():
    """Google sign-ups must pick a username and password before using the app."""
    if not current_user.is_authenticated or current_user.password_set:
        return None
    endpoint = request.endpoint or ""
    if endpoint in ("static", "auth.set_password", "auth.logout") or endpoint.startswith("lang."):
        return None
    if request.path.startswith("/chat/api/"):  # fetch() callers expect JSON, not a redirect
        return jsonify({"error": "password setup required"}), 403
    return redirect(url_for("auth.set_password"))


@auth_bp.route("/set-password", methods=["GET", "POST"])
@login_required
def set_password():
    """Google sign-ups choose a username and password, so they can also sign in without Google."""
    if current_user.password_set:
        return redirect(url_for(current_user.landing_endpoint()))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        errors = _username_errors(username, current_user) + _new_password_errors(
            password, request.form.get("confirm_password", ""))
        if errors:
            for msg in errors:
                flash(msg, "danger")
            return render_template("auth/set_password.html", username=username)

        old_username = current_user.username
        current_user.username = username
        current_user.set_password(password)
        db.session.commit()
        AuditService.log("PASSWORD_SET", "User", current_user.id,
                         f"Username and password set for {username}" + (f" (was {old_username})" if old_username != username else ""))
        flash(_("បានបង្កើតគណនីរួចរាល់។ ឥឡូវអ្នកអាចចូលដោយប្រើឈ្មោះអ្នកប្រើប្រាស់ ឬអ៊ីមែល និងពាក្យសម្ងាត់។"), "success")
        return redirect(url_for(current_user.landing_endpoint()))

    return render_template("auth/set_password.html", username=current_user.username)


RESEND_SECONDS = int(PasswordResetCode.RESEND_COOLDOWN.total_seconds())


def _clear_reset_session() -> None:
    for key in ("pw_reset_email", "pw_reset_sent_at", "pw_reset_code_id"):
        session.pop(key, None)


@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        if not email:
            flash(_("សូមបញ្ចូលអាសយដ្ឋានអ៊ីមែលរបស់អ្នក។"), "danger")
            return render_template("auth/forgot_password.html", email=email)

        user = _find_user_by_email(email)
        if user and user.is_active and PasswordResetService.send_code(user):
            AuditService.log("PASSWORD_RESET_REQUEST", "User", user.id, f"Password reset code sent to {user.username}")

        # Same next step whether or not the email exists, to protect against email enumeration attacks
        _clear_reset_session()
        session["pw_reset_email"] = email
        session["pw_reset_sent_at"] = time.time()
        return redirect(url_for("auth.verify_reset_code"))

    return render_template("auth/forgot_password.html", email=request.args.get("email", ""))


@auth_bp.route("/forgot-password/verify", methods=["GET", "POST"])
def verify_reset_code():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    email = session.get("pw_reset_email")
    if not email:
        return redirect(url_for("auth.forgot_password"))

    if request.method == "POST":
        code = re.sub(r"\D", "", request.form.get("code", ""))
        user = _find_user_by_email(email)
        record = None
        if len(code) == 6 and user and user.is_active:
            record = PasswordResetService.verify(user, code)

        if record:
            session["pw_reset_code_id"] = record.id
            return redirect(url_for("auth.reset_password"))

        # One message for wrong, expired, locked-out and unknown-email cases
        flash(_("លេខកូដមិនត្រឹមត្រូវ ឬផុតកំណត់ហើយ។ សូមពិនិត្យម្តងទៀត ឬស្នើសុំលេខកូដថ្មី។"), "danger")
        return redirect(url_for("auth.verify_reset_code"))

    elapsed = int(time.time() - session.get("pw_reset_sent_at", 0))
    resend_wait = max(0, RESEND_SECONDS - elapsed)
    expires_in = max(0, int(PasswordResetCode.LIFETIME.total_seconds()) - elapsed)
    return render_template("auth/verify_code.html", email=email, resend_wait=resend_wait, expires_in=expires_in)


@auth_bp.route("/reset-password", methods=["GET", "POST"])
def reset_password():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    code_id = session.get("pw_reset_code_id")
    record = db.session.get(PasswordResetCode, code_id) if code_id else None
    if not record or not record.can_set_password or not record.user.is_active:
        _clear_reset_session()
        flash(_("សម័យកំណត់ពាក្យសម្ងាត់ផុតកំណត់ហើយ។ សូមស្នើសុំលេខកូដថ្មី។"), "danger")
        return redirect(url_for("auth.forgot_password"))
    user = record.user
    email = user.email

    if request.method == "POST":
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        errors = _new_password_errors(password, confirm_password)

        if errors:
            for msg in errors:
                flash(msg, "danger")
            return render_template("auth/reset_password.html", email=email)

        PasswordResetService.consume(record, password)
        _clear_reset_session()
        AuditService.log("PASSWORD_RESET", "User", user.id, f"Password reset successful for {user.username}")
        flash(_("ពាក្យសម្ងាត់របស់អ្នកត្រូវបានកំណត់ឡើងវិញដោយជោគជ័យ។ សូមចូលប្រើប្រាស់។"), "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/reset_password.html", email=email)


