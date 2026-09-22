# app/routes/menu_routes.py
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required

from app.i18n import gettext as _
from utils.decorators import require_permission
from app.services.menu_service import MENU_ITEMS
from app.services.page_feature_service import PageFeatureService
from app.services.audit_service import AuditService

menu_bp = Blueprint("menu", __name__, url_prefix="/menu-control")

# Offered durations for "disable temporarily", in minutes.
DURATIONS = [15, 30, 60, 120, 240]


@menu_bp.route("/")
@login_required
@require_permission("manage_menu")
def index():
    statuses = {key: PageFeatureService.status(key) for key in MENU_ITEMS}
    return render_template("menu/index.html", items=MENU_ITEMS, statuses=statuses, durations=DURATIONS)


@menu_bp.route("/<key>/enable", methods=["POST"])
@login_required
@require_permission("manage_menu")
def enable(key: str):
    if key not in MENU_ITEMS:
        abort(404)
    PageFeatureService.set_enabled(key, True)
    AuditService.log("UPDATE", "PageFeature", None, f"Enabled menu item: {key}")
    flash(_("បានធ្វើបច្ចុប្បន្នភាពស្ថានភាពម៉ឺនុយ។"), "success")
    return redirect(url_for("menu.index"))


@menu_bp.route("/<key>/disable", methods=["POST"])
@login_required
@require_permission("manage_menu")
def disable(key: str):
    if key not in MENU_ITEMS:
        abort(404)
    minutes = request.form.get("minutes", type=int)
    if minutes and minutes in DURATIONS:
        PageFeatureService.disable_for(key, minutes)
        AuditService.log("UPDATE", "PageFeature", None, f"Disabled menu item: {key} for {minutes} minutes")
    else:
        PageFeatureService.set_enabled(key, False)
        AuditService.log("UPDATE", "PageFeature", None, f"Disabled menu item: {key} indefinitely")
    flash(_("បានធ្វើបច្ចុប្បន្នភាពស្ថានភាពម៉ឺនុយ។"), "success")
    return redirect(url_for("menu.index"))
