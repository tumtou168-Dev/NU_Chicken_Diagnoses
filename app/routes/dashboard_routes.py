# app/routes/dashboard_routes.py
from flask import Blueprint, render_template, abort
from flask_login import login_required, current_user

from app.services.dashboard_service import DashboardService
from app.services.page_feature_service import PageFeatureService

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/dashboard")


@dashboard_bp.route("/")
@login_required
def index():
    # Plain "User" accounts have no admin/doctor overview to see; keep them on diagnosis instead.
    if not (current_user.has_role("Admin") or current_user.has_role("Doctor")):
        abort(403)
    if not PageFeatureService.is_enabled("dashboard"):
        return render_template("layouts/maintenance.html")
    return render_template("dashboard/index.html", d=DashboardService.build(current_user))
