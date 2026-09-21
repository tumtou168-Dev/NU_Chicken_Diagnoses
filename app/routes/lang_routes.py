# app/routes/lang_routes.py
from flask import Blueprint, abort, redirect, request

from app.i18n import COOKIE_NAME, LANGUAGES, safe_next_url

lang_bp = Blueprint("lang", __name__, url_prefix="/lang")


@lang_bp.route("/<code>")
def switch(code: str):
    """Remember the visitor's language in a cookie and go back to the page they were on."""
    if code not in LANGUAGES:
        abort(404)
    response = redirect(safe_next_url(request.args.get("next")))
    response.set_cookie(COOKIE_NAME, code, max_age=60 * 60 * 24 * 365, samesite="Lax", secure=request.is_secure)
    return response
