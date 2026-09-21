# app/routes/dashboard_routes.py
from flask import Blueprint, render_template
from flask_login import login_required, current_user

from app.services.dashboard_service import DashboardService

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/dashboard")


@dashboard_bp.route("/")
@login_required
def index():
    return render_template("dashboard/index.html", d=DashboardService.build(current_user))
