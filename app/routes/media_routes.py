# app/routes/media_routes.py
import os

from flask import Blueprint, Response, abort, current_app, send_from_directory

from app.models.stored_file import StoredFile
from app.services.file_store import FOLDERS

media_bp = Blueprint("media", __name__, url_prefix="/media")

# Filenames are random and never reused, so a browser can keep a copy for good.
CACHE_FOREVER = "public, max-age=31536000, immutable"


@media_bp.route("/<folder>/<filename>")
def serve(folder: str, filename: str):
    """An uploaded file from the database, or from disk for uploads made before the move."""
    if folder not in FOLDERS or filename != os.path.basename(filename):
        abort(404)
    stored = StoredFile.query.get(f"{folder}/{filename}")
    if stored is not None:
        response = Response(stored.data, mimetype=stored.content_type)
    else:
        response = send_from_directory(os.path.join(current_app.static_folder, "uploads", folder), filename)
    response.headers["Cache-Control"] = CACHE_FOREVER
    return response
