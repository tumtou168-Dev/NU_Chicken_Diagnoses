#app/routes/permission_routes.py
from flask import Blueprint, render_template, redirect, url_for, flash, abort
from flask_login import login_required
from app.i18n import gettext as _
from app.forms.permission_forms import (PermissionCreateForm, PermissionEditForm,
                                        PermissionConfirmDeleteForm )
from app.services.permission_service import PermissionService
from app.services.audit_service import AuditService

permission_bp = Blueprint("tbl_permissions", __name__, url_prefix="/permissions")

@permission_bp.route("/")
@login_required
def index():
    permissions = PermissionService.get_permission_all()
    return render_template("permission/index.html", permissions = permissions)

@permission_bp.route("/<int:permission_id>")
@login_required
def detail(permission_id: int):
    permission = PermissionService.get_permission_by_id(permission_id)
    if permission is None:
        abort(404)
    return render_template("permission/detail.html", permission=permission)

@permission_bp.route("/create", methods=["GET", "POST"])
@login_required
def create():
    form = PermissionCreateForm()
    if form.validate_on_submit():
        data = {
            "code": form.code.data,
            "name": form.name.data,
            "module": form.module.data,
            "description": form.description.data,
        }
        
        permission = PermissionService.create_permission(data)
        AuditService.log("CREATE", "Permission", permission.id, f"Created permission: {permission.code}")
        flash(_("បានបង្កើតសិទ្ធិ '%(code)s' ដោយជោគជ័យ។", code=permission.code), "success")
        return redirect(url_for("tbl_permissions.index"))
    
    return render_template("permission/create.html", form=form)

@permission_bp.route("/<int:permission_id>/edit", methods=["GET", "POST"])
@login_required
def edit(permission_id: int):
    permission = PermissionService.get_permission_by_id(permission_id)
    if permission is None:
        abort(404)
        
    form = PermissionEditForm(original_permission=permission, obj=permission)
    
    if form.validate_on_submit():
        data= {
            "code": form.code.data,
            "name": form.name.data,
            "module": form.module.data,
            "description": form.description.data,
        }
        
        PermissionService.update_permission(permission, data)
        AuditService.log("UPDATE", "Permission", permission.id, f"Updated permission: {permission.code}")
        flash(_("បានកែប្រែសិទ្ធិ '%(code)s' ដោយជោគជ័យ។", code=permission.code), "success")
        return redirect(
            url_for("tbl_permissions.detail", permission_id=permission.id)
        )
        
    return render_template("permission/edit.html", form=form, permission=permission)

@permission_bp.route("/<int:permission_id>/delete", methods=["GET"])
@login_required
def delete_confirm(permission_id: int):
    permission = PermissionService.get_permission_by_id(permission_id)
    if permission is None:
        abort(404)
        
    form = PermissionConfirmDeleteForm()
    return render_template(
        "permission/delete_confirm.html", 
        permission = permission, 
        form = form,
    )
    
@permission_bp.route("/<int:permission_id>/delete", methods=["POST"])
@login_required
def delete(permission_id: int):
    permission = PermissionService.get_permission_by_id(permission_id)
    if permission is None:
        abort(404)
        
    permission_code = permission.code
    PermissionService.delete_permission(permission)
    AuditService.log("DELETE", "Permission", permission_id, f"Deleted permission: {permission_code}")
    flash(_("បានលុបសិទ្ធិដោយជោគជ័យ។"), "success")
    return redirect(url_for("tbl_permissions.index"))
