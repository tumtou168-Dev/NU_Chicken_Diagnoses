# app/routes/user_routes.py
from flask import Blueprint, render_template, redirect, url_for, flash, abort, request
from flask_login import login_required, current_user
from app.i18n import gettext as _
from app.forms.user_forms import(
    UserCreateForm,
    UserEditForm,
    UserConfirmDeleteForm,
)
from app.services.user_service import UserService
from app.services.audit_service import AuditService
from app.services.expert_system_service import CaseService
from utils.timezone import now_kh

# blueprint name define endpoint prefix: tbl_users.*
user_bp = Blueprint("tbl_users", __name__, url_prefix="/users")


def _delete_blocked_message(user):
    """Admin and Doctor accounts are protected from deletion: admins run the system,
    doctors approve rules and answer farmers in chat. Returns the reason, or None."""
    if user.has_role("Admin"):
        return _("មិនអាចលុបគណនីអ្នកគ្រប់គ្រងបានទេ។")
    if user.has_role("Doctor"):
        return _("មិនអាចលុបគណនីពេទ្យបានទេ។")
    return None


@user_bp.route("/")
@login_required
def index():
    # Only Admin can view user list
    if not current_user.has_role("Admin"):
        abort(403)
    page = request.args.get("page", 1, type=int)
    pager = UserService.get_page(page)
    form = UserCreateForm()
    return render_template("users/index.html", pager=pager, users=pager.items, counts=UserService.counts(), form=form)

@user_bp.route("/profile")
@login_required
def profile():
    cases = CaseService.get_by_user(current_user.id)
    scored = [c.confidence for c in cases if c.confidence is not None]
    permissions = {}
    for role in current_user.roles:
        for perm in role.permissions:
            permissions.setdefault(perm.module, {})[perm.code] = perm.name
    stats = {
        "cases": len(cases),
        "avg_confidence": round(sum(scored) / len(scored), 1) if scored else None,
        "days": max((now_kh() - current_user.created_at).days, 0),
    }
    return render_template(
        "users/profile.html",
        user=current_user,
        stats=stats,
        recent_cases=cases[:5],
        permissions={m: sorted(p.values()) for m, p in sorted(permissions.items())},
    )

@user_bp.route("/<int:user_id>")
@login_required
def detail(user_id: int):
    # Only Admin can view other user details
    if not current_user.has_role("Admin") and current_user.id != user_id:
        abort(403)

    user = UserService.get_user_by_id(user_id)
    if user is None:
        abort(404)
    return render_template("users/detail.html", user=user)

@user_bp.route("/create", methods=["GET", "POST"])
@login_required
def create():
    # Only Admin can create users
    if not current_user.has_role("Admin"):
        abort(403)

    form = UserCreateForm()
    if request.method == "POST":
        if form.validate_on_submit():
            data = {
                "username": form.username.data,
                "email": form.email.data,
                "full_name": form.full_name.data,
                "is_active": form.is_active.data,
            }
            password = form.password.data
            role_id = form.role_id.data or None
            
            user = UserService.create_user(data, password, role_id)
            AuditService.log("CREATE", "User", user.id, f"Created user: {user.username}")
            flash(_("បានបង្កើតអ្នកប្រើប្រាស់ '%(username)s' ដោយជោគជ័យ។", username=user.username), "success")
            return redirect(url_for("tbl_users.index"))
        
        page = request.args.get("page", 1, type=int)
        pager = UserService.get_page(page)
        return render_template("users/index.html", pager=pager, users=pager.items, counts=UserService.counts(), form=form, show_create_modal=True)
    
    return redirect(url_for("tbl_users.index", open_create=1))

@user_bp.route("/<int:user_id>/edit", methods=["GET", "POST"])
@login_required
def edit(user_id: int):
    # Only Admin can edit other users, users can edit themselves (if implemented, but usually restricted)
    # For now, let's restrict to Admin or self
    if not current_user.has_role("Admin") and current_user.id != user_id:
        abort(403)

    user = UserService.get_user_by_id(user_id)
    if user is None:
        abort(404)
        
    is_admin = current_user.has_role("Admin")
    form = UserEditForm(original_user=user, obj=user)
    if not is_admin:
        # Self-service profile edit: role and active status are admin-only.
        del form.role_id
        del form.is_active
    
    if form.validate_on_submit():
        data = {
            "username": form.username.data,
            "email": form.email.data,
            "full_name": form.full_name.data,
            "is_active": form.is_active.data if is_admin else user.is_active,
        }
        password = form.password.data or None
        role_id = (form.role_id.data or None) if is_admin else None
        
        UserService.update_user(user, data, password, role_id)
        UserService.set_avatar(user, form.avatar.data, form.remove_avatar.data)
        AuditService.log("UPDATE", "User", user.id, f"Updated user: {user.username}")
        flash(_("បានកែប្រែអ្នកប្រើប្រាស់ '%(username)s' ដោយជោគជ័យ។", username=user.username), "success")
        
        # Redirect logic: Admin -> list, User -> profile or detail
        if current_user.has_role("Admin"):
            return redirect(url_for("tbl_users.detail", user_id=user.id))
        else:
            return redirect(url_for("tbl_users.profile"))
    
    return render_template("users/edit.html", form=form, user=user)


@user_bp.route("/<int:user_id>/delete", methods=["GET"])
@login_required
def delete_confirm(user_id: int):
    if not current_user.has_role("Admin"):
        abort(403)

    # Prevent deleting self
    if current_user.id == user_id:
        flash(_("អ្នកមិនអាចលុបគណនីរបស់ខ្លួនឯងបានទេ។"), "danger")
        return redirect(url_for("tbl_users.index"))

    user = UserService.get_user_by_id(user_id)
    if user is None:
        abort(404)

    blocked = _delete_blocked_message(user)
    if blocked:
        flash(blocked, "danger")
        return redirect(url_for("tbl_users.index"))

    form = UserConfirmDeleteForm()
    return render_template("users/delete_confirm.html", user=user, form=form)


@user_bp.route("/<int:user_id>/delete", methods=["POST"])
@login_required
def delete(user_id: int):
    if not current_user.has_role("Admin"):
        abort(403)

    # Prevent deleting self
    if current_user.id == user_id:
        flash(_("អ្នកមិនអាចលុបគណនីរបស់ខ្លួនឯងបានទេ។"), "danger")
        return redirect(url_for("tbl_users.index"))

    user = UserService.get_user_by_id(user_id)
    if user is None:
        abort(404)

    blocked = _delete_blocked_message(user)
    if blocked:
        flash(blocked, "danger")
        return redirect(url_for("tbl_users.index"))

    username = user.username
    UserService.delete_user(user)
    AuditService.log("DELETE", "User", user_id, f"Deleted user: {username}")
    flash(_("បានលុបអ្នកប្រើប្រាស់ដោយជោគជ័យ។"), "success")
    return redirect(url_for("tbl_users.index"))
