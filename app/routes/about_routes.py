# app/routes/about_routes.py
from flask import Blueprint, render_template

about_bp = Blueprint("about", __name__, url_prefix="/about")


@about_bp.route("/credits")
def credits():
    """Public credits page: lecturer, institution, project team, knowledge sources and technology."""
    return render_template("about/credits.html")
